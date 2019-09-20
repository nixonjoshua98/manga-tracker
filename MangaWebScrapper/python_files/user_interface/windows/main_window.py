import threading
import operator
import functions
import webbrowser

import tkinter as tk
import tkinter.ttk as ttk

import database.queries

import user_interface.widgets as widgets
import user_interface.windows as windows

from enums import MangaStatusEnum
import web_scrapper.manganelo as manganelo


class Application(widgets.RootWindow):
	""" Class which will run the entire UI """

	table_headings = [
		"ID", "Manga Title", "Chapter Read", "Latest Chapter"
	]

	def __init__(self, download_controller):
		# ------------------------------------------ #
		super().__init__("Web Scrapper", "800x400")

		self.download_controller = download_controller
		self.sort_function = lambda manga: manga.sort(key=lambda m: m.latest_chapter - m.chapters_read, reverse=True)

		# - Create attributes
		self.table = None
		self.status_dropdown = None
		self.search_entry = None
		self.search_btn = None
		self.right_click = None

		self.current_search = None

		self.child_windows = {
			"edit_window": None,
			"downloads_window": None,
			"search_results_window": None
		}

		# - Create the UI
		self.create_toolbar()
		self.create_table()
		self.create_right_click_menu()

		# - Post the right click menu on right click at cursor x, y
		self.table.bind("<Button-3>", lambda e: self.right_click.post(e.x_root, e.y_root))

	"""
	Creates the toolbar which is located at the top of the window,
	all toolbar UI widgets should be created in this method
	"""
	def create_toolbar(self):
		# - Frames
		toolbar_frame = tk.Frame(self, relief=tk.SUNKEN, borderwidth=1)
		btn_frame = tk.Frame(toolbar_frame, relief=tk.RAISED, borderwidth=1)
		dropdown_frame = tk.Frame(toolbar_frame, relief=tk.RAISED, borderwidth=1)

		# - Left side widgets
		self.status_dropdown = widgets.Dropdown(dropdown_frame, MangaStatusEnum.all_prettify(), self.update_table)

		# - Right side widgets
		downloads_btn = ttk.Button(btn_frame, text="Downloads", command=self.toggle_downloads_window)
		self.search_entry = ttk.Entry(btn_frame)
		self.search_btn = ttk.Button(btn_frame, text="Search", command=self.search_btn_callback)

		# - Widget placement
		toolbar_frame.pack(fill=tk.X)
		dropdown_frame.pack(side=tk.LEFT, fill=tk.X, padx=3, pady=3)
		btn_frame.pack(side=tk.RIGHT, fill=tk.X, padx=3, pady=3)

		self.status_dropdown.pack(side=tk.LEFT, padx=3, pady=3)
		self.search_btn.pack(side=tk.RIGHT, padx=3, pady=3)
		self.search_entry.pack(side=tk.RIGHT, padx=3, pady=3)
		downloads_btn.pack(side=tk.RIGHT, padx=3, pady=3)

	""" Creates the main table which is used to display the data queried from the database """
	def create_table(self):
		# - Variables
		table_callbacks = {"Double-1": self.on_row_selected}

		# - Frames
		table_frame = tk.Frame(self)

		# - Widgets
		self.table = widgets.Treeview(table_frame, self.table_headings, (50, 500, 100, 130), table_callbacks)

		# - Widget placement
		table_frame.pack(expand=True, fill=tk.BOTH)
		self.table.pack(expand=True, fill=tk.BOTH)

		self.update_table()

	def create_right_click_menu(self):
		sort_menu_layout = (
			("ID (asc)",                 "sort_manga_by_id"),
			("Title (asc)",              "sort_manga_by_title"),
			("Latest Chapter (dsc)",     "sort_manga_by_latest_chapter"),
			("Chapters Available (dsc)", "sort_manga_by_chapters_available")
		)

		open_in_menu_layout = (
			("Explorer", "open_manga_in_explorer"),
			("Browser", "open_manga_in_browser"),
		)

		# Create the menus
		self.right_click = tk.Menu(self.table, tearoff=0)
		sort_menu = tk.Menu(self.right_click, tearoff=0)
		open_in_menu = tk.Menu(self.right_click, tearoff=0)

		# Add the callbacks
		for txt, callback in sort_menu_layout:
			sort_menu.add_command(label=txt, command=getattr(self, callback))

		for txt, callback in open_in_menu_layout:
			open_in_menu.add_command(label=txt, command=getattr(self, callback))

		self.right_click.add_cascade(label="Open In", menu=open_in_menu)
		self.right_click.add_cascade(label="Sort Table", menu=sort_menu)

	""" Re-populate the table with the database results """
	def update_table(self):
		status_enum_val = MangaStatusEnum.str_to_int(self.status_dropdown.get())

		query_results = database.queries.manga_select_all_with_status(status_enum_val)

		if query_results is None:
			return

		# Do sorting
		if self.sort_function is not None:
			self.sort_function(query_results)

		# Too long a function name
		remove_zero = functions.remove_trailing_zeros_if_zero

		data = []
		for row in query_results:
			data.append((row.id, row.title, remove_zero(row.chapters_read), remove_zero(row.latest_chapter), row.url))

		self.table.clear()
		self.table.populate(data)

	""" Row double click callback - Allow the user to view and edit the row """
	def on_row_selected(self, event=None):
		row = self.table.one()

		if row is None:
			return

		db_row = database.queries.manga_select_one_with_id(row[0])

		try:
			self.child_windows["edit_window"].destroy()
		except AttributeError:
			""" Window is None (this is expected) """

		self.child_windows["edit_window"] = windows.MangaEditWindow(db_row, self.update_table)
		self.child_windows["edit_window"].center_in_root(500, 300)

	""" Toggles the queue window between being visible and hidden """
	def toggle_downloads_window(self, event=None):
		""" Create the downloads window if it hasn't been created before,
		I only want one downloads window to be created """
		if self.child_windows["downloads_window"] is None:
			win = windows.DownloadsWindow(self.download_controller)
			self.child_windows["downloads_window"] = win

		self.child_windows["downloads_window"].show_window()
		self.child_windows["downloads_window"].center_in_root(500, 300)

	def search_btn_callback(self, event=None):
		search_input = self.search_entry.get()

		# Min 3 characters
		if len(search_input) < 3:
			return

		self.search_btn.state(["disabled"])

		self.current_search = manganelo.Search(search_input)

		threading.Thread(target=self.current_search.start).start()

		functions.callback_once_true(self, "finished", self.current_search, lambda: self.search_finished_callback())

	def search_finished_callback(self):
		self.search_btn.state(["!disabled"])

		search_results = self.current_search.results

		win = windows.SearchResultsWindow(search_results, ("Title", "Description"), self.update_table)
		win.geometry(self.geometry())

		if self.child_windows["search_results_window"] is not None:
			self.child_windows["search_results_window"].destroy()

		self.child_windows["search_results_window"] = win

	""" Right click callbacks """

	def sort_manga_by_title(self):
		self.sort_function = lambda manga: manga.sort(key=operator.attrgetter("title"))
		self.update_table()

	def sort_manga_by_id(self):
		self.sort_function = lambda manga: manga.sort(key=operator.attrgetter("id"))
		self.update_table()

	def sort_manga_by_latest_chapter(self):
		self.sort_function = lambda manga: manga.sort(key=operator.attrgetter("latest_chapter"), reverse=True)
		self.update_table()

	def sort_manga_by_chapters_available(self):
		self.sort_function = lambda manga: manga.sort(key=lambda m: m.latest_chapter - m.chapters_read, reverse=True)
		self.update_table()

	def open_manga_in_explorer(self):
		row = self.table.one()

		if row is not None:
			functions.open_manga_in_explorer(row[1])

	def open_manga_in_browser(self):
		row = self.table.one()

		if row is not None:
			webbrowser.open(row[4], new=False)
