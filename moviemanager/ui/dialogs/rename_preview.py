"""Rename preview dialog showing current and new file names."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore


#============================================
class RenamePreviewDialog(PySide6.QtWidgets.QDialog):
	"""Dialog showing a table of current vs new file names.

	Args:
		pairs: List of (current_path, new_path) tuples.
		parent: Parent widget.
	"""

	def __init__(self, pairs: list, parent=None):
		super().__init__(parent)
		self._pairs = pairs
		self.setWindowTitle("Rename Preview")
		self.resize(800, 400)
		self._setup_ui()

	#============================================
	def _setup_ui(self) -> None:
		"""Build the preview table and buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# info label
		count = len(self._pairs)
		info = PySide6.QtWidgets.QLabel(
			f"{count} file(s) will be renamed:"
		)
		layout.addWidget(info)
		# preview table
		self._table = PySide6.QtWidgets.QTableWidget()
		self._table.setColumnCount(2)
		self._table.setHorizontalHeaderLabels(["Current", "New"])
		self._table.setRowCount(len(self._pairs))
		self._table.setEditTriggers(
			PySide6.QtWidgets.QAbstractItemView
			.EditTrigger.NoEditTriggers
		)
		self._table.setSelectionBehavior(
			PySide6.QtWidgets.QAbstractItemView
			.SelectionBehavior.SelectRows
		)
		# stretch columns to fill width
		header = self._table.horizontalHeader()
		header.setStretchLastSection(True)
		header.setSectionResizeMode(
			PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch
		)
		# populate rows
		for row, (src, dst) in enumerate(self._pairs):
			self._table.setItem(
				row, 0,
				PySide6.QtWidgets.QTableWidgetItem(src)
			)
			self._table.setItem(
				row, 1,
				PySide6.QtWidgets.QTableWidgetItem(dst)
			)
		layout.addWidget(self._table)
		# buttons
		btn_layout = PySide6.QtWidgets.QHBoxLayout()
		btn_layout.addStretch()
		ok_btn = PySide6.QtWidgets.QPushButton("Rename")
		ok_btn.setDefault(True)
		ok_btn.clicked.connect(self.accept)
		btn_layout.addWidget(ok_btn)
		cancel_btn = PySide6.QtWidgets.QPushButton("Cancel")
		cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(cancel_btn)
		layout.addLayout(btn_layout)
