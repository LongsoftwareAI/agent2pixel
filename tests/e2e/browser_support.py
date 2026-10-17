"""Use an explicitly configured/system browser or Playwright managed Chromium."""
import os
import shutil


def launch_browser(playwright):
    path = os.getenv('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('chromium-browser')
    options = {'headless': True}
    if path:
        options['executable_path'] = path
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        options['args'] = ['--no-sandbox']
    return playwright.chromium.launch(**options)
