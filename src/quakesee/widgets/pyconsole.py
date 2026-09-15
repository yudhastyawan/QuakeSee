from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

class PyConsole(RichJupyterWidget):
    def __init__(self, parent=None):
        RichJupyterWidget.__init__(self, parent)
        self.banner = ''
        self.kernel_banner = ''

        self._create_kernel_manager()

    def _create_kernel_manager(self):
        # Create an in-process kernel
        kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel(show_banner=False)
        kernel_manager.kernel.shell.banner1 = ""
        kernel = kernel_manager.kernel
        kernel.gui = 'qt'

        kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client

    def push_kernel(self, kernel_dict):
        self.kernel_manager.kernel.shell.push(kernel_dict)

    def reset_kernel(self):
        self.reset(True)

    def run_kernel(self, text):
        self._append_plain_text(
            text, False
        )
        self.execute()