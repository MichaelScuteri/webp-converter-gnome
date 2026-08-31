#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GdkPixbuf, GLib, Gtk


APP_ID = "io.itsterminal.WebPConverter"
APP_ROOT = Path(__file__).resolve().parent.parent
APP_SHARE_DIR = APP_ROOT / "share" / APP_ID
ICONS_DIR = APP_SHARE_DIR / "icons"
APP_ICON = (
    APP_ROOT
    / "share"
    / "icons"
    / "hicolor"
    / "scalable"
    / "apps"
    / f"{APP_ID}.svg"
)

EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".webp")
LIBWEBP = "cwebp"

selected_images = []


class WebPConverterWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("WebP Converter")
        self.set_default_size(360, 500)
        self.set_resizable(True)

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        self.set_titlebar(header_bar)

        self.total_savings_label = Gtk.Label()
        self.image_sizes = {}

        self.stats_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=str(ICONS_DIR / "stats.svg"),
            width=24,
            height=24,
            preserve_aspect_ratio=True,
        )
        self.stats_image = Gtk.Image.new_from_pixbuf(self.stats_pixbuf)
        self.stats_image.set_size_request(24, 24)

        self.back_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=str(ICONS_DIR / "back.svg"),
            width=24,
            height=24,
            preserve_aspect_ratio=True,
        )
        self.back_image = Gtk.Image.new_from_pixbuf(self.back_pixbuf)
        self.back_image.set_size_request(24, 24)

        self.stats_button = Gtk.Button()
        self.stats_button.set_child(self.stats_image)
        self.stats_button.connect("clicked", self.on_stats_button_clicked)
        header_bar.pack_start(self.stats_button)
        self.stats_button.hide()

        css = b"""
        .button {
            background: #3584E4;
            border-radius: 16px;
            color: white;
        }

        .splash-title {
            font-size: 24px;
            font-weight: 800;
            margin-top: -30px;
        }

        .splash-image {
            margin-top: -80px;
        }

        .selected-images {
            border: 1px solid;
            border-radius: 10px;
            padding: 5px;
        }

        .image-box {
            border: 1px solid #CCCCCC;
            border-radius: 8px;
        }

        .group-title {
            font-weight: bold;
            font-size: 18px;
            padding-bottom: 5px;
        }

        .total-title {
            font-weight: bold;
            font-size: 16px;
        }

        .image-box-content {
            border-radius: 8px;
            padding: 5px 10px;
        }
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.stack = Gtk.Stack()
        self.set_child(self.stack)

        self.add_splash_screen()
        self.add_main_view()
        self.add_stats_view()
        self.stack.set_visible_child_name("splash_screen")

    @staticmethod
    def clear_box(box):
        child = box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            box.remove(child)
            child = next_child

    def add_splash_screen(self):
        parent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=45)
        parent_box.set_valign(Gtk.Align.CENTER)
        parent_box.set_halign(Gtk.Align.CENTER)
        parent_box.set_vexpand(True)

        splash_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        splash_box.set_valign(Gtk.Align.CENTER)
        splash_box.set_halign(Gtk.Align.CENTER)

        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        button_box.set_valign(Gtk.Align.CENTER)
        button_box.set_halign(Gtk.Align.CENTER)

        logo_size = 150
        original = GdkPixbuf.Pixbuf.new_from_file(str(APP_ICON))
        scaled = original.scale_simple(
            logo_size,
            logo_size,
            GdkPixbuf.InterpType.BILINEAR,
        )

        texture = Gdk.Texture.new_for_pixbuf(scaled)
        image = Gtk.Picture.new_for_paintable(texture)
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        image.set_can_shrink(False)
        image.get_style_context().add_class("splash-image")

        title_label = Gtk.Label(label="WebP Converter")
        title_label.set_xalign(0.5)
        title_label.get_style_context().add_class("splash-title")
        summary_label = Gtk.Label(label="The fastest way to convert to WebP")
        summary_label.set_xalign(0.5)

        start_button = Gtk.Button(label="Select Images")
        start_button.set_margin_start(50)
        start_button.set_margin_end(50)
        start_button.get_style_context().add_class("button")
        start_button.connect("clicked", self.on_select_images_clicked)

        splash_box.append(image)
        splash_box.append(title_label)
        splash_box.append(summary_label)
        button_box.append(start_button)
        parent_box.append(splash_box)
        parent_box.append(button_box)
        self.stack.add_named(parent_box, "splash_screen")

    def add_stats_view(self):
        self.stats_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.stats_vbox.set_valign(Gtk.Align.CENTER)
        self.stats_vbox.set_halign(Gtk.Align.CENTER)
        self.stats_vbox.set_margin_top(20)
        self.stats_vbox.set_margin_start(10)
        self.stats_vbox.set_margin_end(10)
        self.stats_vbox.set_margin_bottom(20)

        self.image_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.image_scrolled_window = Gtk.ScrolledWindow()
        self.image_scrolled_window.set_min_content_width(300)
        self.image_scrolled_window.set_min_content_height(400)
        self.image_scrolled_window.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        self.image_scrolled_window.set_child(self.image_box)

        self.total_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.total_box.set_margin_top(10)

        self.no_images_label = Gtk.Label(
            label="Convert images to display statistics"
        )
        self.stats_vbox.append(self.image_scrolled_window)
        self.stats_vbox.append(self.total_box)
        self.stack.add_named(self.stats_vbox, "stats_view")
        self.update_stats_view()

    def update_stats_view(self):
        total_savings = 0.0
        self.clear_box(self.image_box)

        if self.image_sizes:
            for index, (image_name, sizes) in enumerate(self.image_sizes.items()):
                original_size, converted_size = sizes
                original_size_mb = float(original_size.removesuffix("MB"))
                converted_size_mb = float(converted_size.removesuffix("MB"))
                total_savings += original_size_mb - converted_size_mb

                max_length = 25
                truncated_name = (
                    image_name[: max_length - 3] + "..."
                    if len(image_name) > max_length
                    else image_name
                )

                image_stats_line = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=5
                )
                image_name_label = Gtk.Label(label=truncated_name)
                image_name_label.set_halign(Gtk.Align.START)
                size_label = Gtk.Label(
                    label=f"{original_size} âž {converted_size}"
                )
                size_label.set_halign(Gtk.Align.END)

                spacer = Gtk.Box()
                spacer.set_hexpand(True)
                image_stats_line.append(image_name_label)
                image_stats_line.append(spacer)
                image_stats_line.append(size_label)
                self.image_box.append(image_stats_line)

                if index < len(self.image_sizes) - 1:
                    self.image_box.append(
                        Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                    )

            self.total_savings_label.set_text(
                f"Total Reduction: {round(total_savings, 2)} MB"
            )
            if self.total_savings_label.get_parent() is None:
                self.total_box.append(self.total_savings_label)
        else:
            self.image_box.append(self.no_images_label)

    def on_stats_button_clicked(self, _widget):
        if self.stack.get_visible_child_name() == "main_view":
            self.stack.set_visible_child_name("stats_view")
            self.stats_button.set_child(self.back_image)
        else:
            self.stack.set_visible_child_name("main_view")
            self.stats_button.set_child(self.stats_image)

    def add_main_view(self):
        try:
            self.output_dir = subprocess.check_output(
                ["xdg-user-dir", "PICTURES"], text=True
            ).strip()
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        except (OSError, subprocess.SubprocessError):
            self.output_dir = str(Path.home() / "Pictures")

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_vbox.set_valign(Gtk.Align.CENTER)
        main_vbox.set_halign(Gtk.Align.CENTER)
        main_vbox.set_margin_top(20)
        main_vbox.set_margin_start(25)
        main_vbox.set_margin_end(25)
        main_vbox.set_margin_bottom(20)

        images_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        images_group.set_hexpand(True)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)

        self.select_images_button = Gtk.Button(label="Select Images")
        self.select_images_button.set_margin_top(10)
        self.select_images_button.connect("clicked", self.on_select_images_clicked)

        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.set_margin_top(10)
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        self.cancel_button.hide()

        button_box.append(self.select_images_button)
        button_box.append(self.cancel_button)
        images_group.append(button_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_min_content_height(50)
        scrolled_window.set_max_content_height(100)
        scrolled_window.set_margin_top(20)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.get_style_context().add_class("selected-images")

        drop_target_main = Gtk.DropTarget.new(
            type=Gdk.FileList, actions=Gdk.DragAction.COPY
        )
        drop_target_main.connect("drop", self.on_dnd_drop)
        scrolled_window.add_controller(drop_target_main)

        self.selected_images_label = Gtk.Label(label="No images selected.")
        self.selected_images_label.set_xalign(0.5)
        self.selected_images_label.set_wrap(True)
        self.selected_images_label.set_max_width_chars(50)
        scrolled_window.set_child(self.selected_images_label)
        images_group.append(scrolled_window)
        main_vbox.append(images_group)

        output_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        output_group.set_hexpand(True)
        self.select_output_button = Gtk.Button(label="Output Directory")
        self.select_output_button.set_margin_top(10)
        self.select_output_button.connect("clicked", self.on_select_output_clicked)
        output_group.append(self.select_output_button)

        self.output_dir_label = Gtk.Label(label=self.output_dir)
        self.output_dir_label.set_xalign(0.5)
        self.output_dir_label.set_wrap(True)
        self.output_dir_label.set_max_width_chars(50)
        self.output_dir_label.set_margin_top(5)
        output_group.append(self.output_dir_label)
        main_vbox.append(output_group)

        quality_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        quality_group.set_hexpand(True)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.scale.set_value(75)
        self.scale.set_digits(0)
        self.scale.set_hexpand(True)
        self.scale.set_size_request(275, -1)
        self.scale.connect("value-changed", self.on_scale_value_changed)
        quality_group.append(self.scale)

        self.quality_label = Gtk.Label(
            label=f"Compression Quality: {int(self.scale.get_value())}"
        )
        quality_group.append(self.quality_label)
        main_vbox.append(quality_group)

        convert_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        convert_group.set_margin_start(35)
        convert_group.set_margin_end(35)
        convert_group.set_hexpand(True)
        self.button = Gtk.Button(label="Convert Images")
        self.button.set_margin_top(20)
        self.button.connect("clicked", self.on_convert_clicked)
        self.button.set_sensitive(False)
        convert_group.append(self.button)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_hexpand(True)
        self.progress_bar.set_margin_top(20)
        self.progress_bar.set_opacity(0)
        convert_group.append(self.progress_bar)
        main_vbox.append(convert_group)

        self.output_label = Gtk.Label()
        main_vbox.append(self.output_label)
        self.stack.add_named(main_vbox, "main_view")

        self.dialog = None
        self.failed_images = []

    def on_select_images_clicked(self, _widget):
        self.dialog = Gtk.FileChooserNative(
            title="Select Images",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Select",
            cancel_label="Cancel",
        )
        self.dialog.set_select_multiple(True)
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Image files")
        for extension in EXTENSIONS:
            filter_images.add_pattern(f"*{extension}")
            filter_images.add_pattern(f"*{extension.upper()}")
        self.dialog.add_filter(filter_images)
        self.dialog.connect("response", self.on_file_dialog_response)
        self.dialog.show()

    def on_file_dialog_response(self, dialog, response):
        self.stack.set_visible_child_name("main_view")
        self.stats_button.show()
        if response == Gtk.ResponseType.ACCEPT:
            global selected_images
            selected_images.extend(
                file.get_path()
                for file in dialog.get_files()
                if file.get_path()
            )
            self.refresh_selection_controls()
        dialog.destroy()
        self.dialog = None

    def refresh_selection_controls(self):
        if selected_images:
            self.selected_images_label.set_text(
                ", ".join(Path(path).name for path in selected_images)
            )
            self.cancel_button.show()
            self.button.set_css_classes(["button"])
            self.button.set_sensitive(True)
        else:
            self.selected_images_label.set_text("No images selected.")
            self.cancel_button.hide()
            self.button.set_sensitive(False)

        self.progress_bar.set_opacity(0)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("")
        self.output_label.set_text("")

    def on_dnd_drop(self, _drop_target, file_list, _x, _y):
        global selected_images
        if not isinstance(file_list, Gdk.FileList):
            return False

        for gfile in file_list.get_files():
            file_path = gfile.get_path()
            if file_path and file_path.lower().endswith(EXTENSIONS):
                selected_images.append(file_path)

        self.refresh_selection_controls()
        return True

    def on_cancel_clicked(self, _widget):
        global selected_images
        selected_images = []
        self.button.get_style_context().remove_class("button")
        self.refresh_selection_controls()

    def on_select_output_clicked(self, _widget):
        self.dialog = Gtk.FileChooserNative(
            title="Select Output Directory",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="Select",
            cancel_label="Cancel",
        )
        self.dialog.connect("response", self.on_output_dir_dialog_response)
        self.dialog.show()

    def on_output_dir_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_file()
            if folder.get_path():
                self.output_dir = folder.get_path()
                self.output_dir_label.set_text(self.output_dir)
        dialog.destroy()
        self.dialog = None

    def on_scale_value_changed(self, widget):
        self.quality_label.set_text(
            f"Compression Quality: {int(widget.get_value())}"
        )

    def on_convert_clicked(self, _widget):
        self.image_sizes = {}
        quality = str(int(self.scale.get_value()))
        output_dir = self.output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        if selected_images:
            self.failed_images = []
            self.button.get_style_context().remove_class("button")
            self.button.set_sensitive(False)
            self.progress_bar.set_opacity(1)
            self.progress_bar.set_fraction(0.0)
            self.progress_bar.set_text("Starting conversion...")
            self.output_label.set_text("")
            self.update_stats_view()
            threading.Thread(
                target=self.convert_images,
                args=(selected_images.copy(), quality, output_dir),
                daemon=True,
            ).start()

    def convert_images(self, images, quality, output_dir):
        converted_sizes = {}
        failed_images = []
        total_images = len(images)

        for index, image in enumerate(images):
            input_size = Path(image).stat().st_size / (1024 * 1024)
            original_size = f"{round(input_size, 2)}MB"
            image_name = Path(image).name
            output_file = Path(output_dir) / f"{Path(image_name).stem}.webp"

            try:
                result = subprocess.run(
                    [LIBWEBP, "-quiet", "-q", quality, image, "-o", str(output_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                if result.returncode == 0 and output_file.exists():
                    converted_mb = output_file.stat().st_size / (1024 * 1024)
                    converted_sizes[image_name] = (
                        original_size,
                        f"{round(converted_mb, 2)}MB",
                    )
                else:
                    failed_images.append(image_name)
            except (OSError, subprocess.SubprocessError) as error:
                print(f"Failed to convert {image_name}: {error}", file=sys.stderr)
                failed_images.append(image_name)

            fraction = (index + 1) / total_images
            GLib.idle_add(self.progress_bar.set_fraction, fraction)
            GLib.idle_add(
                self.progress_bar.set_text,
                f"Converting... {int(fraction * 100)}%",
            )

        GLib.idle_add(self.conversion_complete, converted_sizes, failed_images)

    def conversion_complete(self, converted_sizes, failed_images):
        self.image_sizes = converted_sizes
        self.failed_images = failed_images
        total_images = len(selected_images)
        failed = len(self.failed_images)
        converted = total_images - failed
        self.output_label.set_text(
            f"Converted {converted} of {total_images} images."
        )

        if failed:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to convert the following images:",
                secondary_text="\n".join(self.failed_images),
            )
            dialog.connect("response", lambda current_dialog, _response: current_dialog.destroy())
            dialog.show()

        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Conversion complete.")
        self.update_stats_view()
        return GLib.SOURCE_REMOVE


class WebPConverterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = WebPConverterWindow(self)
        window.present()


def main():
    app = WebPConverterApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())