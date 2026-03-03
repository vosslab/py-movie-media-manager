"""Rename preview dialog showing current and new file names."""

# Standard Library
import os

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
	def _compute_base_dir(self) -> str:
		"""Find the longest common directory prefix across all paths.

		Returns:
			Common base directory string.
		"""
		# collect all source and destination paths
		all_paths = []
		for src, dst in self._pairs:
			all_paths.append(src)
			all_paths.append(dst)
		base = os.path.commonpath(all_paths)
		# if commonpath returned a file, go up to its parent
		if not os.path.isdir(base):
			base = os.path.dirname(base)
		return base

	#============================================
	@staticmethod
	def _short_base_label(base_dir: str) -> str:
		"""Shorten a base directory to the last 2-3 path components.

		Args:
			base_dir: Full base directory path.

		Returns:
			Shortened path string with leading ellipsis.
		"""
		parts = base_dir.rstrip(os.sep).split(os.sep)
		# show last 3 components at most
		if len(parts) > 3:
			short = os.sep.join(parts[-3:])
			label = f".../{short}/"
		else:
			label = f"{base_dir}/"
		return label

	#============================================
	def _setup_ui(self) -> None:
		"""Build the preview table and buttons."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		# compute common base directory for relative display
		base_dir = self._compute_base_dir()
		short_base = self._short_base_label(base_dir)
		# info label
		count = len(self._pairs)
		info = PySide6.QtWidgets.QLabel(
			f"{count} file(s) will be renamed (in {short_base}):"
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
		# populate rows with relative paths for readability
		for row, (src, dst) in enumerate(self._pairs):
			rel_src = os.path.relpath(src, base_dir)
			rel_dst = os.path.relpath(dst, base_dir)
			self._table.setItem(
				row, 0,
				PySide6.QtWidgets.QTableWidgetItem(rel_src)
			)
			self._table.setItem(
				row, 1,
				PySide6.QtWidgets.QTableWidgetItem(rel_dst)
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
