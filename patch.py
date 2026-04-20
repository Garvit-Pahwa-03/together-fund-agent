"""
patch.py
Patches crewai's broken telemetry import on Streamlit Cloud.
crewai==0.28.8 imports pkg_resources in its telemetry module
which is not available in newer uv-based environments.
This patch must be imported before any crewai import.
"""
import sys
import types

# Create a fake pkg_resources module that satisfies crewai's needs
fake_pkg = types.ModuleType("pkg_resources")


def get_distribution(name):
    class FakeDist:
        version = "0.0.0"
    return FakeDist()


def require(name):
    return []


fake_pkg.get_distribution = get_distribution
fake_pkg.require = require
fake_pkg.DistributionNotFound = Exception
fake_pkg.VersionConflict = Exception

sys.modules["pkg_resources"] = fake_pkg