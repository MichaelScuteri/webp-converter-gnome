#!/usr/bin/env python3

import os
import subprocess
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Adw, Gdk, GdkPixbuf
import threading

extensions = (".png", ".jpg", ".jpeg", ".tiff", ".webp")

selected_images = []
image_sizes = {}

libwebp = "cwebp"  

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

        #stats icon load
        self.stats_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename="data/icons/stats.svg",
            width=24, height=24,  
            preserve_aspect_ratio=True
        )
        self.stats_image = Gtk.Image.new_from_pixbuf(self.stats_pixbuf)
        self.stats_image.set_size_request(24, 24)

        #back icon load
        self.back_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename="data/icons/back.svg",
            width=24, height=24,  
            preserve_aspect_ratio=True
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
            padding: 5px;
            padding-left: 10px;
            padding-right: 10px;
        }
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        #stack to switch between pages
        self.stack = Gtk.Stack()
        self.set_child(self.stack)

        self.add_splash_screen()
        self.add_main_view()
        self.add_stats_view()

        self.stack.set_visible_child_name("splash_screen")

    def add_splash_screen(self):
        parent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=45)
        parent_box.set_valign(Gtk.Align.CENTER) 
        parent_box.set_halign(Gtk.Align.CENTER) 
        parent_box.set_vexpand(True)  

        splash_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        splash_box.set_valign(Gtk.Align.CENTER) 
        splash_box.set_halign(Gtk.Align.CENTER) 
        splash_box.set_vexpand(False)  

        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        button_box.set_valign(Gtk.Align.CENTER) 
        button_box.set_halign(Gtk.Align.CENTER)  
        button_box.set_vexpand(False)  

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename="data/icons/io.itsterminal.WebPConverter.svg", 
            width=100, height=100, 
            preserve_aspect_ratio=True
        )
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.set_size_request(100, 100)

        title_label = Gtk.Label(label="WebP Converter")
        title_label.set_xalign(0.5) 
        title_label.get_style_context().add_class("splash-title")
        summary_label = Gtk.Label(label="The fastest way to convert to WebP")
        summary_label.set_xalign(0.5)  

        start_button = Gtk.Button(label="Select Images")
        start_button.set_hexpand(False)  
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

        #conversion box
        self.image_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.image_box.get_style_context().add_class("image-box")

        self.image_scrolled_window = Gtk.ScrolledWindow()
        self.image_scrolled_window.set_min_content_width(300)  
        self.image_scrolled_window.set_min_content_height(400)  
        self.image_scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC) 
        self.image_scrolled_window.set_child(self.image_box) 

        #total savings box
        self.total_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.total_box.set_margin_top(10)

        self.no_images_label = Gtk.Label(label="Convert images to display statistics")
        self.total_savings_label = Gtk.Label()

        self.stats_vbox.append(self.image_scrolled_window)
        self.stats_vbox.append(self.total_box)

        self.stack.add_named(self.stats_vbox, "stats_view")
        self.update_stats_view()

    def update_stats_view(self):
        total_savings = 0.0

        for child in list(self.image_box):
            self.image_box.remove(child)

        if hasattr(self, 'image_sizes') and self.image_sizes:
            if self.no_images_label.get_parent():
                self.image_box.remove(self.no_images_label)

            for index, (image_name, (original_size, converted_size)) in enumerate(self.image_sizes.items()):
                original_size_mb = float(original_size.replace("MB", ""))
                converted_size_mb = float(converted_size.replace("MB", ""))
                savings = original_size_mb - converted_size_mb
                total_savings += savings

                MAX_CHAR_LENGTH = 25

                if len(image_name) > MAX_CHAR_LENGTH:
                    truncated_image_name = image_name[:MAX_CHAR_LENGTH - 3] + "..."  
                else:
                    truncated_image_name = image_name

                image_stats_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

                image_name_label = Gtk.Label(label=truncated_image_name)
                image_name_label.set_halign(Gtk.Align.START)

                size_text = f"{original_size} ➝ {converted_size}"
                size_label = Gtk.Label(label=size_text)
                size_label.set_halign(Gtk.Align.END)

                spacer = Gtk.Box()
                spacer.set_hexpand(True)

                image_stats_line.append(image_name_label)
                image_stats_line.append(size_label)

                self.image_box.append(image_stats_line)

                if index < len(self.image_sizes) - 1:
                    separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                    self.image_box.append(separator)

            self.total_savings_label.set_text(f"Total Reduction: {round(total_savings, 2)} MB")
            if self.total_savings_label.get_parent() is None:
                self.total_box.append(self.total_savings_label)

        else:
            self.image_box.append(self.no_images_label)

    def on_stats_button_clicked(self, widget):
        if self.stack.get_visible_child_name() == "main_view":
            self.stack.set_visible_child_name("stats_view")
            self.stats_button.set_child(self.back_image)
        else:
            self.stack.set_visible_child_name("main_view")
            self.stats_button.set_child(self.stats_image)

    def add_main_view(self):
        try:
            self.output_dir = subprocess.check_output(["xdg-user-dir", "PICTURES"]).decode("utf-8").strip()
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
        except Exception as e:
            self.output_dir = os.path.expanduser("~/Pictures")

        self.images_selected = False

        #main vertical box container
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_vbox.set_valign(Gtk.Align.CENTER) 
        main_vbox.set_halign(Gtk.Align.CENTER) 
        main_vbox.set_margin_top(20)
        main_vbox.set_margin_start(25)
        main_vbox.set_margin_end(25)
        main_vbox.set_margin_bottom(20)

        #group 1: select images and cancel selection
        images_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        images_group.set_hexpand(True)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_hexpand(False)

        #button to select images
        self.select_images_button = Gtk.Button(label="Select Images")
        self.select_images_button.set_halign(Gtk.Align.CENTER)
        self.select_images_button.set_hexpand(False)
        self.select_images_button.set_vexpand(False)
        self.select_images_button.set_margin_top(10)
        self.select_images_button.connect("clicked", self.on_select_images_clicked)

        #button to cancel selected images
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.set_halign(Gtk.Align.CENTER)
        self.cancel_button.set_hexpand(False)
        self.cancel_button.set_vexpand(False)
        self.cancel_button.set_margin_top(10)
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        self.cancel_button.hide()

        button_box.append(self.select_images_button)
        button_box.append(self.cancel_button)

        images_group.append(button_box)
        
        #label for selected images
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_min_content_height(50)  
        scrolled_window.set_max_content_height(100)  
        scrolled_window.set_margin_top(20)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.get_style_context().add_class("selected-images")

        #drag and drop
        drop_target_main = Gtk.DropTarget.new(type=Gdk.FileList, actions=Gdk.DragAction.COPY)
        drop_target_main.connect('drop', self.on_dnd_drop)
        scrolled_window.add_controller(drop_target_main)

        # Label for selected images
        self.selected_images_label = Gtk.Label(label="No images selected.")
        self.selected_images_label.set_xalign(0.5)  
        self.selected_images_label.set_wrap(True)
        self.selected_images_label.set_max_width_chars(50)
        scrolled_window.set_child(self.selected_images_label)  

        images_group.append(scrolled_window)

        main_vbox.append(images_group)

        #group 2: select output directory
        output_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        output_group.set_hexpand(True)

        #button for output directory
        self.select_output_button = Gtk.Button(label="Output Directory")
        self.select_output_button.set_halign(Gtk.Align.CENTER)
        self.select_output_button.set_hexpand(False)
        self.select_output_button.set_vexpand(False)
        self.select_output_button.set_margin_top(10)
        self.select_output_button.connect("clicked", self.on_select_output_clicked)
        output_group.append(self.select_output_button)

        #label for selected output directory
        self.output_dir_label = Gtk.Label(label=(f"{self.output_dir}"))
        self.output_dir_label.set_xalign(0.5)
        self.output_dir_label.set_wrap(True)
        self.output_dir_label.set_max_width_chars(50)
        self.output_dir_label.set_margin_top(5)
        output_group.append(self.output_dir_label)

        main_vbox.append(output_group)

        #group 3: image Quality
        quality_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        quality_group.set_hexpand(True)

        #quality input
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self.scale.set_value(75)
        self.scale.set_digits(0)
        self.scale.set_hexpand(True)
        self.scale.set_size_request(275, -1)
        self.scale.connect("value-changed", self.on_scale_value_changed)
        quality_group.append(self.scale)

        #label for current quality
        self.quality_label = Gtk.Label(label=f"Compression Quality: {int(self.scale.get_value())}")
        self.quality_label.set_xalign(0.5)
        quality_group.append(self.quality_label)

        main_vbox.append(quality_group)

        #group 4: convert button and progress
        convert_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        convert_group.set_margin_start(35)
        convert_group.set_margin_end(35)
        convert_group.set_hexpand(True)

        #convert button
        self.button = Gtk.Button(label="Convert Images")
        self.button.set_halign(Gtk.Align.CENTER)
        self.button.set_hexpand(False)
        self.button.set_vexpand(False)
        self.button.set_margin_top(20)
        self.button.connect("clicked", self.on_convert_clicked)
        self.button.set_sensitive(False) 
        convert_group.append(self.button)

        #progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_hexpand(True)
        self.progress_bar.set_vexpand(False)
        self.progress_bar.set_margin_top(20)
        self.progress_bar.set_margin_bottom(0)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("")  
        self.progress_bar.set_opacity(0)  
        convert_group.append(self.progress_bar)

        main_vbox.append(convert_group)

        #output label
        self.output_label = Gtk.Label(label="")
        self.output_label.set_xalign(0.5)
        self.output_label.set_margin_top(0)
        main_vbox.append(self.output_label)

        self.stack.add_named(main_vbox, "main_view")

        self.dialog = None
        self.failed_images = []

    def on_select_images_clicked(self, widget):
        self.dialog = Gtk.FileChooserNative(
            title="Select Images",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Select",
            cancel_label="Cancel"
        )
        self.dialog.set_select_multiple(True)
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Image files")
        for ext in extensions:
            filter_images.add_pattern(f"*{ext}")
        self.dialog.add_filter(filter_images)

        self.dialog.connect("response", self.on_file_dialog_response)
        self.dialog.show()

    def on_file_dialog_response(self, dialog, response):
        self.stack.set_visible_child_name("main_view")
        self.stats_button.show()
        if response == Gtk.ResponseType.ACCEPT:
            files = dialog.get_files()
            new_selected_files = [f.get_path() for f in files]
            global selected_images
            selected_images.extend(new_selected_files)
            if selected_images:
                filenames = [os.path.basename(f) for f in selected_images]
                filenames_text = ", ".join(filenames)
                self.selected_images_label.set_text(filenames_text)
                self.cancel_button.show()
                self.button.set_css_classes(['button'])
                self.button.set_sensitive(True)
                self.progress_bar.set_opacity(0)  
                self.progress_bar.set_fraction(0.0)
                self.progress_bar.set_text("")  
                self.output_label.set_text("")  
            else:
                self.selected_images_label.set_text("No images selected.")
                self.cancel_button.hide()
        dialog.destroy()
        self.dialog = None
    
    def on_dnd_drop(self, drop_target, file_list, x, y):
        global selected_images
        if isinstance(file_list, Gdk.FileList):
            new_files = []
            for gfile in file_list.get_files():
                file_path = gfile.get_path()
                if file_path and file_path.endswith(extensions):
                    selected_images.append(file_path)
                    new_files.append(os.path.basename(file_path))

            if new_files:
                filenames_text = ", ".join([os.path.basename(f) for f in selected_images])
                self.selected_images_label.set_text(filenames_text)
                self.cancel_button.show()
                self.button.set_sensitive(True)
        return True

    def on_cancel_clicked(self, widget):
        global selected_images
        selected_images = [] 
        self.selected_images_label.set_text("No images selected.")
        self.button.get_style_context().remove_class("button")
        self.cancel_button.hide()
        self.button.set_sensitive(False)
        self.progress_bar.set_opacity(0)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("")  
        self.output_label.set_text("")  

    def on_select_output_clicked(self, widget):
        self.dialog = Gtk.FileChooserNative(
            title="Select Output Directory",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="Select",
            cancel_label="Cancel"
        )

        self.dialog.connect("response", self.on_output_dir_dialog_response)
        self.dialog.show()

    def on_output_dir_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            folder = dialog.get_file()
            self.output_dir = folder.get_path()
            self.output_dir_label.set_text(self.output_dir)
        dialog.destroy()
        self.dialog = None

    def on_scale_value_changed(self, widget):
        current_value = int(widget.get_value())
        self.quality_label.set_text(f"Current Quality: {current_value}")

    def on_convert_clicked(self, widget):
        self.image_sizes = {}

        quality = str(int(self.scale.get_value()))
        output_dir = self.output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if selected_images:
            self.failed_images = []
            self.button.get_style_context().remove_class("button")
            self.button.set_sensitive(False)
            self.progress_bar.set_opacity(1)  
            self.progress_bar.set_fraction(0.0)
            self.progress_bar.set_text("Starting conversion...")
            self.output_label.set_text("")
            self.update_stats_view()
            threading.Thread(target=self.convert_images, args=(selected_images.copy(), quality, output_dir)).start()

    def convert_images(self, images, quality, output_dir):
        total_images = len(images)
        global image_sizes

        for index, image in enumerate(images):
            input_file = image  
            input_size = os.stat(input_file).st_size / (1024 * 1024)
            original_size = f"{round(input_size, 2)}MB"

            image_name = os.path.basename(image)
            output_file = os.path.join(output_dir, os.path.splitext(image_name)[0] + ".webp")

            try:
                result = subprocess.call(
                    [libwebp, "-quiet", "-q", quality, input_file, "-o", output_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result == 0 and os.path.exists(output_file):
                    converted_size_mb = os.stat(output_file).st_size / (1024 * 1024)
                    converted_size = f"{round(converted_size_mb, 2)}MB"
                    image_sizes[image_name] = (original_size, converted_size)
                else:
                    self.failed_images.append(image_name)
            except Exception as e:
                print(e)
                self.failed_images.append(image_name)
            fraction = (index + 1) / total_images
            GLib.idle_add(self.progress_bar.set_fraction, fraction)
            GLib.idle_add(self.progress_bar.set_text, f"Converting... {int(fraction * 100)}%")
        GLib.idle_add(self.conversion_complete)

        self.image_sizes = image_sizes
        print(image_sizes)

    def conversion_complete(self):
        total_images = len(selected_images)
        failed = len(self.failed_images)
        converted = total_images - failed
        self.output_label.set_text(f"Converted {converted} of {total_images} images.")

        if failed > 0:
            error_message = "\n".join(self.failed_images)
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to convert the following images:",
                secondary_text=error_message
            )
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.show()
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Conversion complete.")

        GLib.idle_add(self.update_stats_view)

class WebPConverterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.itsterminal.WebPConverter')

    def do_activate(self):
        win = WebPConverterWindow(self)
        win.present()

def main():
    app = WebPConverterApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
