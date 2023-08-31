import argparse
import importlib
import json
import logging as log
import sys
import traceback
from pathlib import Path
from time import time

import torch

import postprocessing_data as pp
import preprocessing_data as prep
from inference_tools.loop_tools import loop_inference, get_exec_time
from io_adapter import IOAdapter
from io_model_wrapper import PyTorchIOModelWrapper
from reporter.report_writer import ReportWriter
from transformer import PyTorchTransformer


def cli_argument_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('-m', '--model',
                        help='Path to PyTorch model with format .pt.',
                        type=str,
                        dest='model')
    parser.add_argument('-w', '--weights',
                        help='Path to file with format .pth with weights of PyTorch model',
                        type=str,
                        default=None,
                        dest='weights')
    parser.add_argument('-mm', '--module',
                        help='Module with model architecture.',
                        default='torchvision.models',
                        type=str,
                        dest='module')
    parser.add_argument('-mn', '--model_name',
                        help='Model name from the module.',
                        required=True,
                        type=str,
                        dest='model_name')
    parser.add_argument('-i', '--input',
                        help='Path to data.',
                        required=True,
                        type=str,
                        nargs='+',
                        dest='input')
    parser.add_argument('-in', '--input_names',
                        help='Names of the input tensors',
                        required=True,
                        default=None,
                        type=prep.names_arg,
                        dest='input_names')
    parser.add_argument('-is', '--input_shapes',
                        help='Input tensor shapes',
                        default=None,
                        type=str,
                        dest='input_shapes')
    parser.add_argument('--mean',
                        help='Parameter mean',
                        default=None,
                        type=str,
                        dest='mean')
    parser.add_argument('--input_scale',
                        help='Parameter input scale',
                        type=str,
                        dest='input_scale')
    parser.add_argument('--output_names',
                        help='Name of the output tensors.',
                        default='output',
                        type=str,
                        nargs='+',
                        dest='output_names')
    parser.add_argument('-b', '--batch_size',
                        help='Batch size.',
                        default=1,
                        type=int,
                        dest='batch_size')
    parser.add_argument('-l', '--labels',
                        help='Labels mapping file.',
                        default=None,
                        type=str,
                        dest='labels')
    parser.add_argument('-nt', '--number_top',
                        help='Number of top results.',
                        default=5,
                        type=int,
                        dest='number_top')
    parser.add_argument('-t', '--task',
                        help='Task type determines the type of output processing '
                             'method. Available values: feedforward - without'
                             'postprocessing (by default), classification - output'
                             'is a vector of probabilities.',
                        choices=['feedforward', 'classification'],
                        default='feedforward',
                        type=str,
                        dest='task')
    parser.add_argument('-ni', '--number_iter',
                        help='Number of inference iterations.',
                        default=1,
                        type=int,
                        dest='number_iter')
    parser.add_argument('--raw_output',
                        help='Raw output without logs.',
                        default=False,
                        type=bool,
                        dest='raw_output')
    parser.add_argument('-d', '--device',
                        help='Specify the target device to infer on CPU or '
                             'NVIDIA_GPU (CPU by default)',
                        default='CPU',
                        type=str,
                        dest='device')
    parser.add_argument('--model_type',
                        help='Model type for inference',
                        choices=['scripted', 'baseline'],
                        default='scripted',
                        type=str,
                        dest='model_type')
    parser.add_argument('--inference_mode',
                        help='Inference mode',
                        default=True,
                        type=bool,
                        dest='inference_mode')
    parser.add_argument('--tensor_rt_precision',
                        help='TensorRT precision FP16, FP32.'
                             ' Applicable only for hosts with NVIDIA GPU and pytorch built with TensorRT support',
                        type=str,
                        default=None,
                        dest='tensor_rt_precision')
    parser.add_argument('--layout',
                        help='Parameter input layout',
                        default=None,
                        type=str,
                        dest='layout')
    parser.add_argument('--input_type',
                        help='Parameter input type',
                        default=None,
                        type=str,
                        dest='input_type')
    parser.add_argument('--report_path',
                        type=Path,
                        default=Path(__file__).parent / 'pytorch_inference_report.json',
                        dest='report_path',
                        help='Path to json benchmark report path, default: ./pytorch_inference_report.json')
    parser.add_argument('--time', required=False, default=0, type=int,
                        dest='time',
                        help='Optional. Time in seconds to execute topology.')
    parser.add_argument('--num_inter_threads',
                        help='Number of threads used for parallelism between independent operations',
                        default=None,
                        type=int,
                        dest='num_inter_threads')
    parser.add_argument('--num_intra_threads',
                        help='Number of threads used within an individual op for parallelism',
                        default=None,
                        type=int,
                        dest='num_intra_threads')
    args = parser.parse_args()

    return args


def set_thread_num(num_inter_threads, num_intra_threads):
    def validate(num):
        if num < 0:
            raise ValueError(f'Incorrect thread count: {num}')

    if num_inter_threads:
        validate(num_inter_threads)
        torch.set_num_interop_threads(num_inter_threads)
        log.info(f'The number of threads for inter-op parallelism: {num_inter_threads}')
    if num_intra_threads:
        validate(num_intra_threads)
        torch.set_num_threads(num_intra_threads)
        log.info(f'The number of threads for intra-op parallelism: {num_intra_threads}')


def get_device_to_infer(device):
    log.info('Get device for inference')
    if device == 'CPU':
        log.info(f'Inference will be executed on {device}')
        return torch.device('cpu')
    elif device == 'NVIDIA_GPU':
        log.info(f'Inference will be executed on {device}')
        return torch.device('cuda')
    else:
        log.info(f'The device {device} is not supported')
        raise ValueError('The device is not supported')


def is_gpu_available():
    return torch.cuda.is_available()


def get_tensor_rt_dtype(tensor_rt_precision):
    if tensor_rt_precision:
        tensor_rt_dtype = None
        if tensor_rt_precision == 'FP32':
            tensor_rt_dtype = torch.float
        elif tensor_rt_precision == 'FP16':
            tensor_rt_dtype = torch.half
        else:
            raise ValueError(f'Unknown TensorRT precision {tensor_rt_precision}')
        return tensor_rt_dtype
    else:
        return None


def load_model_from_module(model_name, module, weights):
    log.info(f'Loading model from module {module}')
    model_cls = importlib.import_module(module).__getattribute__(model_name)
    if weights is None or weights == '':
        log.info('Loading pretrained model')
        return model_cls(weights=True)
    else:
        log.info(f'Loading model with weights from file {weights}')
        model = model_cls()
        model.load_state_dict(torch.load(weights))
        return model


def load_model_from_file(model_path):
    log.info(f'Loading model from path {model_path}')
    file_type = model_path.split('.')[-1]
    supported_extensions = ['pt']
    if file_type not in supported_extensions:
        raise ValueError(f'The file type {file_type} is not supported')
    model = torch.load(model_path)
    return model


def compile_model(module, device, model_type, use_tensorrt, shapes, tensor_rt_dtype):
    if model_type == 'baseline':
        log.info('Inference will be executed on baseline model')
    elif model_type == 'scripted':
        log.info('Inference will be executed on scripted model')
        module = torch.jit.script(module)
    else:
        raise ValueError(f'Model type {model_type} is not supported for inference')
    module.to(device)
    module.eval()

    if use_tensorrt:
        if is_gpu_available():
            import torch_tensorrt
            inputs = [torch_tensorrt.Input(shapes[key], dtype=tensor_rt_dtype) for key in shapes]
            tensor_rt_ts_module = torch_tensorrt.compile(module, inputs=inputs,
                                                         truncate_long_and_double=True,
                                                         enabled_precisions=tensor_rt_dtype)
            return tensor_rt_ts_module
        else:
            raise ValueError('GPU is not available')
    else:
        return module


def inference_pytorch(model, num_iterations, get_slice, input_names, inference_mode, device, test_duration):
    with torch.inference_mode(inference_mode):
        predictions = None
        time_infer = []
        if num_iterations == 1:
            inputs = [torch.tensor(get_slice()[input_name], device=device) for input_name in input_names]
            t0 = time()
            predictions = torch.nn.functional.softmax(model(*inputs), dim=1).to('cpu')
            t1 = time()
            time_infer.append(t1 - t0)
        else:
            # several decorator calls in order to use variables as decorator parameters
            time_infer = loop_inference(num_iterations, test_duration)(inference_iteration)(device, get_slice,
                                                                                            input_names, model)
    return predictions, time_infer


@get_exec_time()
def infer_slice(device, inputs, model):
    model(*inputs)
    if device.type == 'cuda':
        torch.cuda.synchronize()


def inference_iteration(device, get_slice, input_names, model):
    inputs = [torch.tensor(get_slice()[input_name], device=device) for input_name in input_names]
    if device.type == 'cuda':
        torch.cuda.synchronize()
    _, exec_time = infer_slice(device, inputs, model)
    return exec_time


def prepare_output(result, output_names, task):
    if task == 'feedforward':
        return {}
    if (output_names is None) or len(output_names) == 0:
        raise ValueError('The number of output tensors does not match the number of corresponding output names')
    if task == 'classification':
        return {output_names[0]: result.detach().numpy()}
    else:
        raise ValueError(f'Unsupported task {task} to print inference results')


def main():
    log.basicConfig(
        format='[ %(levelname)s ] %(message)s',
        level=log.INFO,
        stream=sys.stdout,
    )
    args = cli_argument_parser()
    report_writer = ReportWriter()
    report_writer.update_framework_info(name='PyTorch', version=torch.__version__)
    report_writer.update_configuration_setup(batch_size=args.batch_size,
                                             iterations_num=args.number_iter,
                                             target_device=args.device)

    try:
        tensor_rt_dtype = get_tensor_rt_dtype(args.tensor_rt_precision)
        args.input_shapes = prep.parse_input_arg(args.input_shapes, args.input_names)
        model_wrapper = PyTorchIOModelWrapper(args.input_shapes, args.batch_size, tensor_rt_dtype, args.input_type)

        args.mean = prep.parse_input_arg(args.mean, args.input_names)
        args.input_scale = prep.parse_input_arg(args.input_scale, args.input_names)
        args.layout = prep.parse_layout_arg(args.layout, args.input_names)
        data_transformer = PyTorchTransformer(prep.create_dict_for_transformer(args))
        io = IOAdapter.get_io_adapter(args, model_wrapper, data_transformer)

        if args.model is not None:
            model = load_model_from_file(args.model)
        else:
            model = load_model_from_module(args.model_name, args.module, args.weights)

        set_thread_num(args.num_inter_threads, args.num_intra_threads)
        device = get_device_to_infer(args.device)
        compiled_model = compile_model(model, device, args.model_type,
                                       args.tensor_rt_precision is not None, args.input_shapes, tensor_rt_dtype)

        for layer_name in args.input_names:
            layer_shape = model_wrapper.get_input_layer_shape(args.model, layer_name)
            log.info(f'Shape for input layer {layer_name}: {layer_shape}')

        log.info(f'Preparing input data {args.input}')
        io.prepare_input(compiled_model, args.input)

        log.info(f'Starting inference (max {args.number_iter} iterations or {args.time} sec) on {args.device}')
        result, inference_time = inference_pytorch(compiled_model, args.number_iter,
                                                   io.get_slice_input,
                                                   args.input_names, args.inference_mode, device,
                                                   args.time)

        log.info('Computing performance metrics')
        inference_result = pp.calculate_performance_metrics_sync_mode(args.batch_size, inference_time)
        report_writer.update_execution_results(**inference_result)
        log.info(f'Write report to {args.report_path}')
        report_writer.write_report(args.report_path)

        if not args.raw_output:
            if args.number_iter == 1:
                try:
                    log.info('Converting output tensor to print results')
                    result = prepare_output(result, args.output_names, args.task)

                    log.info('Inference results')
                    io.process_output(result, log)
                except Exception as ex:
                    log.warning('Error when printing inference results. {0}'.format(str(ex)))

        log.info(f'Performance results:\n{json.dumps(inference_result, indent=4)}')

    except Exception:
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main() or 0)
