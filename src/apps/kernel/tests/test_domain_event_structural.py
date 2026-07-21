"""
Structural guarantees for Module 09 domain events:

- Views never publish domain events (only the service layer may).
- apps/kernel/events/__init__.py never imports apps.notifications (the
  dependency direction is one-way: notifications -> kernel.events, wired
  only through AppConfig.ready(), never the reverse) — this is what keeps
  the system free of circular imports.
"""

import glob
import inspect
import os

from django.test import TestCase

import apps.kernel.events as kernel_events


class DomainEventStructuralTest(TestCase):
    def test_no_views_module_publishes_domain_events(self):
        apps_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # .../src/apps
        views_files = glob.glob(os.path.join(apps_dir, "*", "views.py"))
        self.assertTrue(views_files, "expected to find at least one views.py to scan")

        for path in views_files:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            self.assertNotIn(
                "kernel.events",
                source,
                f"{path} must not import apps.kernel.events — views must not publish events",
            )
            self.assertNotIn(
                "publish(",
                source,
                f"{path} must not call publish() — only the service layer may publish events",
            )

    def test_kernel_events_package_does_not_import_notifications(self):
        source = inspect.getsource(kernel_events)
        import_lines = [
            line.strip()
            for line in source.splitlines()
            if line.strip().startswith("from ") or line.strip().startswith("import ")
        ]
        for line in import_lines:
            self.assertNotIn(
                "notifications",
                line,
                "apps/kernel/events/__init__.py must not import apps.notifications (avoids circular imports)",
            )
            self.assertNotIn(
                "handlers",
                line,
                "apps/kernel/events/__init__.py must not eagerly import handlers.py "
                "(that module depends on apps.notifications and must load lazily via AppConfig.ready())",
            )

    def test_kernel_events_public_surface_is_stable(self):
        self.assertTrue(hasattr(kernel_events, "DomainEvent"))
        self.assertTrue(hasattr(kernel_events, "EventRegistry"))
        self.assertTrue(hasattr(kernel_events, "publish"))
