from pathlib import Path
from datetime import datetime
import os
import shutil
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
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
OUT_DIR = Path(App.user_data_dir if 'App' in globals() else BASE) / 'outputs'
OUT_DIR.mkdir(parents=True, exist_ok=True)


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


class VegRow(BoxLayout):
    def __init__(self, index, **kwargs):
        super().__init__(orientation='horizontal', spacing=dp(6), size_hint_y=None,
                         height=dp(78), padding=dp(4), **kwargs)
        self.index = index
        self.photo = ''

        self.add_widget(Label(text=f'{index}', size_hint_x=None, width=dp(30),
                              color=(0.05, 0.3, 0.15, 1), bold=True))
        self.photo_btn = Button(text='📷 फोटो', size_hint_x=None, width=dp(92))
        self.photo_btn.bind(on_release=self.pick_photo)
        self.add_widget(self.photo_btn)

        self.name = TextInput(hint_text='भाजीचे नाव', multiline=False, size_hint_x=0.42)
        self.price = TextInput(hint_text='₹ किंमत', multiline=False, input_filter='float', size_hint_x=0.25)
        self.add_widget(self.name)
        self.add_widget(self.price)

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
                self.photo_btn.text = '⚠️ पुन्हा'
            else:
                self.photo = local
                self.photo_btn.text = '✓ फोटो'
        except Exception:
            self.photo = ''
            self.photo_btn.text = '⚠️ पुन्हा'

    def data(self):
        return {'photo': self.photo, 'name': self.name.text.strip(), 'price': self.price.text.strip()}


class SNCApp(App):
    def build(self):
        self.title = 'SNC शेतकरी बाजार'
        Window.clearcolor = (0.95, 0.98, 0.94, 1)

        root = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        title = Label(text='SNC शेतकरी बाजार\nपोस्टर मेकर', font_size=dp(24), bold=True,
                      color=(0.0, 0.36, 0.17, 1), size_hint_y=None, height=dp(70))
        root.add_widget(title)

        meta = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, height=dp(110))
        self.date = TextInput(text=datetime.now().strftime('%d/%m/%Y'), multiline=False,
                              hint_text='तारीख')
        self.contact = TextInput(text='9552233488', multiline=False, hint_text='संपर्क क्रमांक')
        self.address = TextInput(text='रामनगर कृषी उत्पन्न बाजार समिती, दुकान न.8, चंद्रपूर महाराष्ट्र -442401',
                                 multiline=False, hint_text='पत्ता')
        meta.add_widget(Label(text='तारीख'))
        meta.add_widget(self.date)
        meta.add_widget(Label(text='संपर्क'))
        meta.add_widget(self.contact)
        meta.add_widget(Label(text='पत्ता'))
        meta.add_widget(self.address)
        root.add_widget(meta)

        header = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        for t, w in [('No.', 30), ('Photo', 92), ('Vegetable', 0), ('Price', 0)]:
            header.add_widget(Label(text=t, size_hint_x=None if w else 1, width=dp(w) if w else 0,
                                    color=(0.1, 0.25, 0.15, 1), bold=True))
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
        generate = Button(text='🖼️ JPG तयार करा', background_color=(0.0, 0.55, 0.24, 1))
        generate.bind(on_release=self.make_poster)
        buttons.add_widget(clear)
        buttons.add_widget(generate)
        root.add_widget(buttons)

        return root

    def clear_all(self, *_):
        for row in self.rows:
            row.name.text = ''
            row.price.text = ''
            row.photo = ''
            row.photo_btn.text = '📷 फोटो'

    def make_poster(self, *_):
        items = [r.data() for r in self.rows]
        filename = f'SNC_Poster_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        output = OUT_DIR / filename
        try:
            generate_poster(items, self.date.text.strip(), self.contact.text.strip(),
                            self.address.text.strip(), str(output))
            self.show_done(str(output))
        except Exception as e:
            self.show_message('Error', str(e))

    def show_done(self, path):
        box = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        box.add_widget(Label(text=f'Poster तयार झाला!\n\n{path}', halign='center'))
        close = Button(text='OK', size_hint_y=None, height=dp(45))
        box.add_widget(close)
        popup = Popup(title='SNC Poster', content=box, size_hint=(0.9, 0.4))
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
