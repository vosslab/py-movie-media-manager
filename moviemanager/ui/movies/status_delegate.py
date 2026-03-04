"""Custom delegate for painting status icon indicators."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# colors for present vs missing indicators
COLOR_PRESENT = PySide6.QtGui.QColor("#4CAF50")
COLOR_PARTIAL = PySide6.QtGui.QColor("#FFC107")
COLOR_MISSING = PySide6.QtGui.QColor("#F44336")


#============================================
class StatusIconDelegate(PySide6.QtWidgets.QStyledItemDelegate):
	"""Paints a green circle for True, red circle for False.

	Reads boolean from UserRole and draws a filled circle
	centered in the cell.
	"""

	#============================================
	def paint(self, painter, option, index) -> None:
		"""Paint status icon as a colored filled circle.

		Args:
			painter: The QPainter to draw with.
			option: Style options for the item.
			index: Model index of the item.
		"""
		# draw the background (selection highlight, etc.)
		self.initStyleOption(option, index)
		style = option.widget.style() if option.widget else PySide6.QtWidgets.QApplication.style()
		style.drawPrimitive(
			PySide6.QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewItem,
			option, painter, option.widget
		)
		# get the boolean flag from UserRole
		flag = index.data(PySide6.QtCore.Qt.ItemDataRole.UserRole)
		if flag is None:
			return
		painter.save()
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing)
		# pick color: supports bool (True/False) and string ("complete"/"partial")
		if flag is True or flag == "complete":
			color = COLOR_PRESENT
		elif flag == "partial":
			color = COLOR_PARTIAL
		else:
			color = COLOR_MISSING
		painter.setBrush(PySide6.QtGui.QBrush(color))
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		# draw a filled circle centered in the cell
		rect = option.rect
		diameter = min(rect.height() - 6, 12)
		cx = rect.left() + (rect.width() - diameter) // 2
		cy = rect.top() + (rect.height() - diameter) // 2
		painter.drawEllipse(cx, cy, diameter, diameter)
		painter.restore()

	#============================================
	def sizeHint(self, option, index) -> PySide6.QtCore.QSize:
		"""Return compact size hint for a single icon column.

		Args:
			option: Style options for the item.
			index: Model index of the item.

		Returns:
			QSize with width for a single icon indicator.
		"""
		size = PySide6.QtCore.QSize(26, option.rect.height())
		return size


# severity level color mapping for parental guide indicators
SEVERITY_COLORS = {
	"None": PySide6.QtGui.QColor("#4CAF50"),      # green
	"Mild": PySide6.QtGui.QColor("#FFC107"),       # yellow
	"Moderate": PySide6.QtGui.QColor("#FF9800"),   # orange
	"Severe": PySide6.QtGui.QColor("#F44336"),     # red
}
COLOR_NO_DATA = PySide6.QtGui.QColor("#9E9E9E")   # gray for missing data


#============================================
class SeverityDelegate(PySide6.QtWidgets.QStyledItemDelegate):
	"""Paints a colored circle for parental guide severity level.

	Reads severity string from UserRole and draws a filled circle
	colored by severity: green (None), yellow (Mild), orange (Moderate),
	red (Severe), gray (no data).
	"""

	#============================================
	def paint(self, painter, option, index) -> None:
		"""Paint severity indicator as a colored filled circle.

		Args:
			painter: The QPainter to draw with.
			option: Style options for the item.
			index: Model index of the item.
		"""
		# draw the background (selection highlight, etc.)
		self.initStyleOption(option, index)
		style = option.widget.style() if option.widget else PySide6.QtWidgets.QApplication.style()
		style.drawPrimitive(
			PySide6.QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewItem,
			option, painter, option.widget
		)
		# get the severity string from UserRole
		severity = index.data(PySide6.QtCore.Qt.ItemDataRole.UserRole)
		# pick color based on severity value
		color = SEVERITY_COLORS.get(severity, COLOR_NO_DATA)
		painter.save()
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing)
		painter.setBrush(PySide6.QtGui.QBrush(color))
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		# draw a filled circle centered in the cell
		rect = option.rect
		diameter = min(rect.height() - 6, 12)
		cx = rect.left() + (rect.width() - diameter) // 2
		cy = rect.top() + (rect.height() - diameter) // 2
		painter.drawEllipse(cx, cy, diameter, diameter)
		painter.restore()

	#============================================
	def sizeHint(self, option, index) -> PySide6.QtCore.QSize:
		"""Return compact size hint for severity icon column.

		Args:
			option: Style options for the item.
			index: Model index of the item.

		Returns:
			QSize with width for a single icon indicator.
		"""
		size = PySide6.QtCore.QSize(26, option.rect.height())
		return size
