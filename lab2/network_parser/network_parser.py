import sys
from pathlib import Path

import onnx
import torch
import torch.nn as nn

project_root = Path(__file__).parents[1]
sys.path.append(str(project_root))

import torch2onnx
from layer_info import (
    Conv2DShapeParam,
    LinearShapeParam,
    MaxPool2DShapeParam,
    ShapeParam,
)
from lib.models.vgg import VGG


def parse_pytorch(model: nn.Module, input_shape=(1, 3, 32, 32)) -> list[ShapeParam]:
    layers = []
    #! <<<========= Implement here =========>>>
    def hook(module: nn.Module, inputs: torch.Tensor, output: torch.Tensor) -> None:
        if isinstance(module, nn.Conv2d):
            N, C, H, W = inputs[0].shape # batch_size, in_channels, in_height, in_width
            R, S = module.kernel_size    # filter_height, filter_width
            E, F = output.shape[2:]      # out_height, out_width
            M = module.out_channels      # out_channels
            U, P = module.stride[0], module.padding[0]
            layers.append(
                Conv2DShapeParam(N, H, W, R, S, E, F, C, M, U, P)
            )
        elif isinstance(module, nn.MaxPool2d):
            N, C, H, W = inputs[0].shape
            kernel_size, stride = module.kernel_size, module.stride
            layers.append(MaxPool2DShapeParam(N, kernel_size, stride))
        elif isinstance(module, nn.Linear):
            N, in_features = inputs[0].shape
            out_features = module.out_features
            layers.append(LinearShapeParam(N, in_features, out_features))

    hooks = []
    for module in model.modules():
        hooks.append(module.register_forward_hook(hook))

    dummy_input = torch.randn(*input_shape)
    model(dummy_input)

    for hook in hooks:
        hook.remove()

    return layers


def parse_onnx(model: onnx.ModelProto) -> list[ShapeParam]:
    layers = []
    #! <<<========= Implement here =========>>>
    def _get_tensor_shape(model: onnx.ModelProto, tensor_name: str):
        inferred_model = onnx.shape_inference.infer_shapes(model)

        # Search for the tensor with the given name
        for value_info in inferred_model.graph.value_info:
            if value_info.name == tensor_name:
                dims = value_info.type.tensor_type.shape.dim
                shape = [dim.dim_value for dim in dims]

                return shape

        # If not found; search the model's inputs
        for input_info in inferred_model.graph.input:
            if input_info.name == tensor_name:
                dims = input_info.type.tensor_type.shape.dim
                shape = [dim.dim_value for dim in dims]

                return shape

        # If still not found; search the model's outputs
        for output_info in inferred_model.graph.output:
            if output_info.name == tensor_name:
                dims = output_info.type.tensor_type.shape.dim
                shape = [dim.dim_value for dim in dims]

                return shape

    inferred_model = onnx.shape_inference.infer_shapes(model)

    for node in inferred_model.graph.node:
        op_type = node.op_type
        input_shape = _get_tensor_shape(model, node.input[0])
        output_shape = _get_tensor_shape(model, node.output[0])

        if op_type == "Conv":
            N, C, H, W = input_shape   # batch_size, in_channels, in_height, in_width
            M, E, F = output_shape[1:] # out_channels, out_height, out_width

            for attr in node.attribute:
                if attr.name == "kernel_shape":
                    R, S = attr.ints
                elif attr.name == "strides":
                    U = attr.ints[0]
                elif attr.name == "pads":
                    P = attr.ints[0]

            layers.append(
                Conv2DShapeParam(N, H, W, R, S, E, F, C, M, U, P)
            )
        elif op_type == "MaxPool":
            N = input_shape[0]

            for attr in node.attribute:
                if attr.name == "kernel_shape":
                    kernel_size = attr.ints[0]
                elif attr.name == "strides":
                    stride = attr.ints[0]

            layers.append(MaxPool2DShapeParam(N, kernel_size, stride))
        elif op_type == "Gemm":
            N = input_shape[0]
            in_features = input_shape[1]
            out_features = output_shape[1]

            layers.append(LinearShapeParam(N, in_features, out_features))

    return layers


def compare_layers(answer, layers):
    if len(answer) != len(layers):
        print(
            f"Layer count mismatch: answer has {len(answer)}, but ONNX has {len(layers)}"
        )

    min_len = min(len(answer), len(layers))

    for i in range(min_len):
        ans_layer = vars(answer[i])
        layer = vars(layers[i])

        diffs = {
            k: (ans_layer[k], layer[k])
            for k in ans_layer
            if k in layer and ans_layer[k] != layer[k]
        }

        if diffs:
            print(f"Difference in layer {i + 1} ({type(answer[i]).__name__}):")
            for k, (ans_val, val) in diffs.items():
                print(f"  {k}: answer = {ans_val}, onnx = {val}")

    if len(answer) > len(layers):
        print(f"Extra layers in answer: {answer[len(layers) :]}")
    elif len(layers) > len(answer):
        print(f"Extra layers in yours: {layers[len(answer) :]}")


def run_tests() -> None:
    """Run tests on the network parser functions."""
    answer = [
        Conv2DShapeParam(N=1, H=32, W=32, R=3, S=3, E=32, F=32, C=3, M=64, U=1, P=1),
        MaxPool2DShapeParam(N=1, kernel_size=2, stride=2),
        Conv2DShapeParam(N=1, H=16, W=16, R=3, S=3, E=16, F=16, C=64, M=192, U=1, P=1),
        MaxPool2DShapeParam(N=1, kernel_size=2, stride=2),
        Conv2DShapeParam(N=1, H=8, W=8, R=3, S=3, E=8, F=8, C=192, M=384, U=1, P=1),
        Conv2DShapeParam(N=1, H=8, W=8, R=3, S=3, E=8, F=8, C=384, M=256, U=1, P=1),
        Conv2DShapeParam(N=1, H=8, W=8, R=3, S=3, E=8, F=8, C=256, M=256, U=1, P=1),
        MaxPool2DShapeParam(N=1, kernel_size=2, stride=2),
        LinearShapeParam(N=1, in_features=4096, out_features=256),
        LinearShapeParam(N=1, in_features=256, out_features=128),
        LinearShapeParam(N=1, in_features=128, out_features=10),
    ]

    # Test with the PyTorch model.
    model = VGG()
    layers_pth = parse_pytorch(model)

    # Define the input shape.
    dummy_input = torch.randn(1, 3, 32, 32)
    # Save the model to ONNX.
    torch2onnx.torch2onnx(model, "parser_onnx.onnx", dummy_input)
    # Load the ONNX model.
    model_onnx = onnx.load("parser_onnx.onnx")
    layers_onnx = parse_onnx(model_onnx)

    # Display results.
    print("PyTorch Network Parser:")
    if layers_pth == answer:
        print("Correct!")
    else:
        print("Wrong!")
        compare_layers(answer, layers_pth)

    print("ONNX Network Parser:")
    if layers_onnx == answer:
        print("Correct!")
    else:
        print("Wrong!")
        compare_layers(answer, layers_onnx)


if __name__ == "__main__":
    run_tests()
