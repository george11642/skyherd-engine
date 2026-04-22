"""SkyHerd Edge — Pi-side H1 runtime.

Exports
-------
EdgeWatcher
    Async loop: capture → detect → publish on MQTT bus.
get_camera
    Factory returning PiCamera or MockCamera based on availability.
MegaDetectorHead
    Hardware-grade detector backed by PytorchWildlife (lazy import).
"""

from skyherd.edge.camera import get_camera
from skyherd.edge.detector import MegaDetectorHead
from skyherd.edge.watcher import EdgeWatcher

__all__ = ["EdgeWatcher", "MegaDetectorHead", "get_camera"]
