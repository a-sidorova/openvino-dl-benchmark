from .framework_parameters_parser import FrameworkParameters


class CppParameters(FrameworkParameters):
    def __init__(self, backend, provider, input_shape, layout, mean, input_scale, thread_count,
                 inference_requests_count):
        self.backend = None
        self.provider = None
        self.input_shape = None
        self.layout = None
        self.mean = None
        self.input_scale = None
        self.thread_count = None
        self.inference_requests_count = None

        if self._parameter_not_is_none(backend):
            self.backend = backend.strip()
        if self._parameter_not_is_none(provider):
            self.provider = provider.strip()
        if self._parameter_not_is_none(input_shape):
            self.input_shape = input_shape.strip()
        if self._parameter_not_is_none(layout):
            self.layout = layout.strip()
        if self._parameter_not_is_none(mean):
            self.mean = mean.strip()
        if self._parameter_not_is_none(input_scale):
            self.input_scale = input_scale.strip()
        if self._parameter_not_is_none(thread_count) and self._int_value_is_correct(thread_count):
            self.thread_count = thread_count
        if self._parameter_not_is_none(inference_requests_count) and self._int_value_is_correct(
                inference_requests_count):
            self.inference_requests_count = inference_requests_count
