from pathlib import Path
from datetime import datetime
import os
import shutil
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.popup import Popup

try:
    from plyer import filechooser
except Exception:
    filechooser = None

from poster_generator import generate_poster

BASE = Path(__file__).parent
OUT_DIR = BASE / 'outputs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Register Marathi/Devanagari font as the app-wide default -----------
# Without this Kivy falls back to Roboto, which has no Devanagari glyphs,
# so every Marathi label/button/textinput shows tofu boxes (▯▯▯).
FONT_REGULAR = str(BASE / 'fonts' / 'NotoSansDevanagari-Regular.ttf')
FONT_BOLD = str(BASE / 'fonts' / 'NotoSansDevanagari-Bold.ttf')
try:
    LabelBase.register(name='Roboto', fn_regular=FONT_REGULAR, fn_bold=FONT_BOLD)
except Exception:
    pass


def android_copy_content_uri(uri: str, dest: Path) -> str:
    """Copy a content:// URI returned by Android's document picker to a local file."""
    if not uri.startswith('content://'):
        return uri
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()
        stream = resolver.openInputStream(autoclass('android.net.Uri').parse(uri))
        with open(dest, 'wb') as f:
            buf = bytearray(1024 * 1024)
            while True:
                n = stream.read(buf)
                if n <= 0:
                    break
                f.write(buf[:n])
        stream.close()
        return str(dest)
    except Exception:
        return uri


def save_jpg_to_gallery(local_path: Path, filename: str):
    """
    Copy the generated JPG into the phone's public Pictures/SNC Poster
    folder via MediaStore, so it shows up in the normal Gallery/Photos
    app instead of being stuck inside the app's private, hard-to-find
    storage. Returns True on success.
    """
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()
        ContentValues = autoclass('android.content.ContentValues')
        MediaImages = autoclass('android.provider.MediaStore$Images$Media')
        VersionCheck = autoclass('android.os.Build$VERSION')

        values = ContentValues()
        values.put('_display_name', filename)
        values.put('mime_type', 'image/jpeg')
        is_new_android = VersionCheck.SDK_INT >= 29
        if is_new_android:
            values.put('relative_path', 'Pictures/SNC Poster')
            values.put('is_pending', 1)

        item_uri = resolver.insert(MediaImages.EXTERNAL_CONTENT_URI, values)
        if item_uri is None:
            return False

        out_stream = resolver.openOutputStream(item_uri)
        with open(local_path, 'rb') as f:
            out_stream.write(f.read())
        out_stream.close()

        if is_new_android:
            done = ContentValues()
            done.put('is_pending', 0)
            resolver.update(item_uri, done, None, None)
        return True
    except Exception as e:
        print('save_jpg_to_gallery failed:', e)
        return False


def request_storage_permission():
    """Old Android (< 10) needs WRITE_EXTERNAL_STORAGE to save to gallery."""
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.WRITE_EXTERNAL_STORAGE])
    except Exception:
        pass


class VegRow(BoxLayout):
    def __init__(self, index, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(6), size_hint_y=None,
                         height=dp(78), padding=dp(4), **kwargs)
        self.index = index
        self.photo = ''

        self.add_widget(Label(text=f'{index}', size_hint_x=None, width=dp(26),
                              color=(0.05, 0.3, 0.15, 1), bold=True))
        self.photo_btn = Button(text='फोटो', size_hint_x=None, width=dp(80))
        self.photo_btn.bind(on_release=self.pick_photo)
        self.add_widget(self.photo_btn)

        self.name = TextInput(hint_text='भाजीचे नाव', multiline=False, size_hint_x=0.36)
        self.price_min = TextInput(hint_text='Min ₹', multiline=False, input_filter='float', size_hint_x=0.17)
        self.price_max = TextInput(hint_text='Max ₹', multiline=False, input_filter='float', size_hint_x=0.17)
        self.add_widget(self.name)
        self.add_widget(self.price_min)
        self.add_widget(self.price_max)

    def pick_photo(self, *_):
        if filechooser is None:
            return
        filechooser.open_file(on_selection=self.selected, filters=['*.png', '*.jpg', '*.jpeg', '*.webp'])

    def selected(self, selection):
        if not selection:
            return
        source = selection[0]
        try:
            ext = '.jpg'
            if '.' in source.lower().split('?')[0]:
                ext = Path(source.split('?')[0]).suffix or '.jpg'
            dest = Path(App.get_running_app().user_data_dir) / f'photo_{self.index}{ext}'
            local = android_copy_content_uri(source, dest)
            if local.startswith('content://'):
                self.photo = ''
                self.photo_btn.text = 'पुन्हा'
            else:
                self.photo = local
                self.photo_btn.text = '✓ फोटो'
        except Exception:
            self.photo = ''
            self.photo_btn.text = 'पुन्हा'

    def data(self):
        min_p = self.price_min.text.strip()
        max_p = self.price_max.text.strip()
        if min_p and max_p:
            price = f'{min_p} ते {max_p}'
        elif min_p:
            price = min_p
        elif max_p:
            price = max_p
        else:
            price = ''
        return {'photo': self.photo, 'name': self.name.text.strip(), 'price': price}


class SNCApp(App):
    def build(self):
        global OUT_DIR
        OUT_DIR = Path(self.user_data_dir) / 'outputs'
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        request_storage_permission()

        self.title = 'SNC शेतकरी बाजार'
        Window.clearcolor = (0.95, 0.98, 0.94, 1)

        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        title = Label(text='SNC शेतकरी बाजार\nपोस्टर मेकर', font_size=dp(24), bold=True,
                      color=(0.0, 0.36, 0.17, 1), size_hint_y=None, height=dp(70), halign='center')
        root.add_widget(title)

        meta = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(44))
        self.date = TextInput(text=datetime.now().strftime('%d/%m/%Y'), multiline=False,
                              hint_text='तारीख')
        meta.add_widget(Label(text='तारीख'))
        meta.add_widget(self.date)
        root.add_widget(meta)

        header = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
        for t, w in [('No.', 26), ('Photo', 80), ('भाजी', 0), ('Min', 0), ('Max', 0)]:
            header.add_widget(Label(text=t, size_hint_x=None if w else 1, width=dp(w) if w else 0,
                                    color=(0.1, 0.25, 0.15, 1), bold=True, font_size=dp(13)))
        root.add_widget(header)

        scroll = ScrollView(do_scroll_x=False)
        self.rows = []
        grid = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for i in range(1, 9):
            row = VegRow(i)
            self.rows.append(row)
            grid.add_widget(row)
        scroll.add_widget(grid)
        root.add_widget(scroll)

        buttons = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        clear = Button(text='सर्व Clear')
        clear.bind(on_release=self.clear_all)
        generate = Button(text='JPG तयार करा', background_color=(0.0, 0.55, 0.24, 1))
        generate.bind(on_release=self.make_poster)
        buttons.add_widget(clear)
        buttons.add_widget(generate)
        root.add_widget(buttons)

        return root

    def clear_all(self, *_):
        for row in self.rows:
            row.name.text = ''
            row.price_min.text = ''
            row.price_max.text = ''
            row.photo = ''
            row.photo_btn.text = 'फोटो'

    def make_poster(self, *_):
        items = [r.data() for r in self.rows]
        if not any(x['photo'] or x['name'] or x['price'] for x in items):
            self.show_message('माहिती नाही', 'किमान एक भाजीचे नाव किंवा किंमत भरा.')
            return
        filename = f'SNC_Poster_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        output = OUT_DIR / filename
        try:
            generate_poster(items, self.date.text.strip(), '', '', str(output))
            saved_to_gallery = save_jpg_to_gallery(output, filename)
            self.show_done(saved_to_gallery)
        except Exception as e:
            self.show_message('Error', str(e))

    def show_done(self, saved_to_gallery):
        box = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        if saved_to_gallery:
            msg = 'Poster तयार झाला!\n\nतुमच्या फोनच्या Gallery मध्ये\n"SNC Poster" नावाच्या फोल्डरमध्ये सेव्ह झाला आहे.'
        else:
            msg = f'Poster तयार झाला, पण Gallery मध्ये सेव्ह करता आलं नाही.\n\nतो इथे आहे:\n{OUT_DIR}'
        box.add_widget(Label(text=msg, halign='center'))
        close = Button(text='OK', size_hint_y=None, height=dp(45))
        box.add_widget(close)
        popup = Popup(title='SNC Poster', content=box, size_hint=(0.9, 0.5))
        close.bind(on_release=popup.dismiss)
        popup.open()

    def show_message(self, title, msg):
        box = BoxLayout(orientation='vertical', padding=dp(15))
        box.add_widget(Label(text=msg))
        btn = Button(text='OK', size_hint_y=None, height=dp(45))
        box.add_widget(btn)
        popup = Popup(title=title, content=box, size_hint=(0.9, 0.4))
        btn.bind(on_release=popup.dismiss)
        popup.open()


if __name__ == '__main__':
    SNCApp().run()
