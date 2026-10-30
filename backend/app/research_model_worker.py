"""Isolated optional worker for locally configured BreaKHis ResNet-18 research weights."""

from __future__ import annotations

import base64
import io
import json
import sys
import traceback
from pathlib import Path


def main() -> int:
    try:
        import torch
        import torch.nn.functional as functional
        from PIL import Image
        from torchvision import models, transforms
        from torch import nn

        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one checkpoint path.")
        checkpoint_path = Path(sys.argv[1]).expanduser()
        request = json.load(sys.stdin)
        image_bytes = base64.b64decode(request["image_base64"], validate=True)
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            original = image.copy()

        try:
            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        except TypeError:
            checkpoint = torch.load(checkpoint_path, map_location="cpu")
        if not isinstance(checkpoint, dict):
            raise ValueError("The selected checkpoint has an unsupported format.")
        class_names = checkpoint.get("class_names")
        if class_names != ["benign", "malignant"]:
            raise ValueError("The selected checkpoint does not use the expected benign/malignant class order.")
        image_size = int(checkpoint.get("image_size", 128))
        if image_size < 64 or image_size > 1024:
            raise ValueError("The checkpoint image size is outside the supported range.")

        explain = bool(request.get("explain", False))
        architecture = checkpoint.get("architecture")
        if architecture == "resnet18":
            model = models.resnet18(weights=None)
            model.fc = nn.Linear(model.fc.in_features, 2)
            model_name = "ResNet-18 BreaKHis research model"
        elif architecture is None and "features.0.weight" in checkpoint.get("model_state_dict", {}):
            class SmallCNN(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.features = nn.Sequential(
                        nn.Conv2d(3, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                        nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                        nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
                        nn.Conv2d(64, 96, 3, padding=1), nn.BatchNorm2d(96), nn.ReLU(inplace=True), nn.AdaptiveAvgPool2d(1),
                    )
                    self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(96, 2))

                def forward(self, x):
                    return self.classifier(self.features(x))

            model = SmallCNN()
            model_name = "Scratch CNN BreaKHis research baseline"
        else:
            raise ValueError("The selected checkpoint architecture is not supported.")
        if explain and architecture is None:
            raise ValueError("Grad-CAM is available only for the ResNet-18 checkpoints.")
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device).eval()
        transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
        ])
        tensor = transform(original).unsqueeze(0).to(device)
        captured: dict[str, torch.Tensor] = {}
        hook_handle = None

        if explain:
            def capture_activation(_module, _inputs, output):
                captured["activation"] = output.detach()

                def capture_gradient(gradient):
                    captured["gradient"] = gradient.detach()
                    return gradient

                output.register_hook(capture_gradient)

            hook_handle = model.layer4[-1].register_forward_hook(capture_activation)

        try:
            if explain:
                logits = model(tensor)
            else:
                with torch.inference_mode():
                    logits = model(tensor)
            scores = torch.softmax(logits, dim=1)[0].detach().cpu().tolist()
            predicted_index = int(logits.argmax(dim=1).item())
            result = {
                "research_only": True,
                "predicted_class": class_names[predicted_index],
                "class_scores": {name: float(score) for name, score in zip(class_names, scores)},
                "score_note": "Softmax model scores; they are not calibrated probabilities or a diagnosis.",
                "model": model_name,
                "training_fold": str(checkpoint.get("fold", "unknown")),
                "training_magnification": str(checkpoint.get("magnification", "unknown")),
                "image_size": image_size,
                "execution_device": str(device),
                "clinical_use": False,
            }
            if explain:
                model.zero_grad(set_to_none=True)
                logits[0, predicted_index].backward()
                activations = captured.get("activation")
                gradients = captured.get("gradient")
                if activations is None or gradients is None:
                    raise RuntimeError("Grad-CAM activations were not captured.")
                weights = gradients.mean(dim=(2, 3), keepdim=True)
                heat = functional.relu((weights * activations).sum(dim=1, keepdim=True))
                heat = functional.interpolate(heat, size=(image_size, image_size), mode="bilinear", align_corners=False)[0, 0]
                minimum, maximum = heat.min(), heat.max()
                heat = (heat - minimum) / (maximum - minimum).clamp_min(1e-8)
                heat_image = Image.fromarray((heat.cpu().numpy() * 255).astype("uint8"), mode="L")
                red = heat_image.resize(original.size, Image.Resampling.BILINEAR)
                green = red.point(lambda value: int(value * 0.22))
                blue = Image.new("L", original.size, 0)
                overlay = Image.blend(original, Image.merge("RGB", (red, green, blue)), 0.42)
                image_output = io.BytesIO()
                overlay.save(image_output, format="PNG", optimize=True)
                result["explanation"] = "Grad-CAM activation overlay for the predicted class. It is a visualization, not evidence of causal reasoning or clinical validity."
                result["grad_cam_overlay_png_base64"] = base64.b64encode(image_output.getvalue()).decode("ascii")
        finally:
            if hook_handle is not None:
                hook_handle.remove()

        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
