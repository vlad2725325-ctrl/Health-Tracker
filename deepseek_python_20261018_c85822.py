import os
from datetime import datetime
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.utils import platform
from kivy.clock import Clock

from auth import AuthStore
from storage import Storage

ERROR_COLOR = [0.94, 0.53, 0.42, 1]
OK_COLOR = [0.44, 0.81, 0.59, 1]

# (название, порция, ккал, белки, жиры, углеводы)
FOODS = [
    ("Куриная грудка", "100 г", 165, 31, 4, 0),
    ("Рис отварной", "150 г", 195, 4, 0, 42),
    ("Овсянка с бананом", "1 порция", 320, 9, 6, 58),
    ("Греческий йогурт", "150 г", 110, 15, 3, 6),
    ("Гречка отварная", "150 г", 165, 6, 2, 32),
    ("Творог 5%", "100 г", 121, 17, 5, 2),
    ("Яйцо варёное", "1 шт", 78, 6, 5, 1),
    ("Яблоко", "1 шт", 80, 0, 0, 21),
]

class Field(BoxLayout):
    label = StringProperty("")
    hint = StringProperty("")
    secret = BooleanProperty(False)
    revealed = BooleanProperty(False)

    @property
    def text(self): return self.ids.field_input.text
    def clear(self): self.ids.field_input.text = ""

class TabButton(Button):
    active = BooleanProperty(False)
    pass

class PrimaryButton(Button):
    pass

class GhostButton(Button):
    pass

class MealRow(BoxLayout):
    name = StringProperty("")
    value = StringProperty("")
    muted = BooleanProperty(False)

class FoodRow(BoxLayout):
    title = StringProperty("")
    sub = StringProperty("")
    macros = StringProperty("")
    selected = BooleanProperty(False)

    def __init__(self, food, on_toggle, **kwargs):
        super().__init__(**kwargs)
        name, amount, kcal, p, f, c = food
        self.food = food
        self.on_toggle = on_toggle
        self.title = name
        self.sub = f"{amount} · {kcal} ккал"
        self.macros = (f"[color=F0866A]Б {p}[/color]   [color=F2C14E]Ж {f}[/color]   [color=6FCF97]У {c}[/color]")

    def toggle(self):
        self.selected = not self.selected
        self.on_toggle(self)

class LoginScreen(Screen):
    mode = StringProperty("login")
    message = StringProperty("")
    message_color = ListProperty(ERROR_COLOR)

    def set_mode(self, mode):
        self.mode = mode
        self.message = ""

    def show_error(self, text):
        self.message_color = ERROR_COLOR
        self.message = text

    def clear_fields(self):
        for name in ("email", "password", "confirm"):
            self.ids[name].clear()
        self.message = ""

    def submit(self):
        app = App.get_running_app()
        email = self.ids.email.text
        password = self.ids.password.text
        if self.mode == "register":
            if password != self.ids.confirm.text:
                self.show_error("Пароли не совпадают"); return
            ok, text = app.auth.register(email, password)
            if not ok: self.show_error(text); return
        ok, text = app.auth.login(email, password)
        if not ok: self.show_error(text); return
        self.clear_fields()
        app.enter()

    def guest(self):
        app = App.get_running_app()
        app.auth.logout()
        self.clear_fields()
        app.enter()

class PermissionsScreen(Screen):
    def proceed(self, want_geo):
        perms = ["android.permission.ACTIVITY_RECOGNITION"]
        if want_geo: perms += ["android.permission.ACCESS_FINE_LOCATION"]
        if platform == "android":
            from android.permissions import request_permissions
            request_permissions(perms)
        self.go_home()

    def go_home(self):
        app = App.get_running_app()
        open(app.flag_path(), "w").close()
        self.manager.current = "home"

class HomeScreen(Screen):
    date_text = StringProperty("")
    eaten = NumericProperty(0)
    left_text = StringProperty("")
    p_text = StringProperty("")
    f_text = StringProperty("")
    c_text = StringProperty("")
    water_text = StringProperty("")
    a1 = NumericProperty(0)
    a2 = NumericProperty(0)
    a3 = NumericProperty(0)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        user = app.auth.current_user() or "guest"
        
        # Получаем данные из БД
        log = app.storage.get_day_food(user)
        water = app.storage.get_water(user)
        goal = app.storage.get_kcal_goal(user)

        now = datetime.now()
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        self.date_text = f"{days[now.weekday()]}, {now.day} {months[now.month - 1]}"

        eaten = sum(e["kcal"] for e in log)
        p = sum(e["p"] for e in log)
        f = sum(e["f"] for e in log)
        c = sum(e["c"] for e in log)
        
        self.eaten = eaten
        self.left_text = str(max(goal - eaten, 0))
        self.p_text, self.f_text, self.c_text = f"{p:.0f} г", f"{f:.0f} г", f"{c:.0f} г"
        self.water_text = f"Вода: {water} из 8"

        total = max(p * 4 + f * 9 + c * 4, 1)
        sweep = min(eaten / goal, 1) * 360 if goal > 0 else 0
        self.a1 = sweep * (p * 4 / total)
        self.a2 = self.a1 + sweep * (f * 9 / total)
        self.a3 = sweep

        box = self.ids.meals
        box.clear_widgets()
        meals_list = ["Завтрак", "Обед", "Ужин", "Перекус"]
        for meal in meals_list:
            kcal = sum(e["kcal"] for e in log if e["meal"] == meal)
            box.add_widget(MealRow(name=meal, value=f"{kcal} ккал" if kcal else "добавить", muted=not kcal))

    def add_water(self):
        user = App.get_running_app().auth.current_user() or "guest"
        current = App.get_running_app().storage.get_water(user)
        App.get_running_app().storage.set_water(user, current + 1)
        self.refresh()

    def remove_water(self):
        user = App.get_running_app().auth.current_user() or "guest"
        current = App.get_running_app().storage.get_water(user)
        App.get_running_app().storage.set_water(user, current - 1)
        self.refresh()

    def logout(self):
        App.get_running_app().auth.logout()
        self.manager.current = "login"

class AddFoodScreen(Screen):
    meal = StringProperty("Ужин")
    sum_text = StringProperty("Ничего не выбрано")
    _search_event = None

    def on_pre_enter(self, *args):
        self.chosen = {}
        field = self.ids.search.ids.field_input
        if not getattr(self, "_bound", False):
            field.bind(text=self.on_search_text)
            self._bound = True
        field.text = ""
        self.show("")
        self.update_sum()

    def on_search_text(self, instance, text):
        # Дебаунс для поиска
        if self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda dt: self.show(text), 0.2)

    def set_meal(self, meal):
        self.meal = meal

    def show(self, query=""):
        box = self.ids.foods
        box.clear_widgets()
        q = query.strip().lower()
        for food in FOODS:
            if q in food[0].lower():
                row = FoodRow(food, self.on_toggle)
                row.selected = food[0] in self.chosen
                box.add_widget(row)

    def on_toggle(self, row):
        if row.selected:
            self.chosen[row.food[0]] = row.food
        else:
            self.chosen.pop(row.food[0], None)
        self.update_sum()

    def update_sum(self):
        if not self.chosen:
            self.sum_text = "Ничего не выбрано"
        else:
            kcal = sum(food[2] for food in self.chosen.values())
            self.sum_text = f"Выбрано: {len(self.chosen)} · {kcal} ккал"

    def add_selected(self):
        app = App.get_running_app()
        user = app.auth.current_user() or "guest"
        for food in self.chosen.values():
            app.storage.add_food(user, self.meal, food)
        self.manager.current = "home"
        
    def go_photo(self):
        app = App.get_running_app()
        app.root.get_screen("photo").meal = self.meal
        app.root.current = "photo"

class PhotoScreen(Screen):
    meal = StringProperty("Ужин")
    total_kcal = StringProperty("0")

    def on_pre_enter(self, *args):
        # Тут будет реальное распознавание, а пока считаем сумму демо-данных
        self.sample = [
            ("Рис отварной", "150 г", 195, 4, 0, 42),
            ("Куриная грудка", "120 г", 198, 37, 5, 0),
            ("Салат овощной", "80 г", 40, 1, 1, 4)
        ]
        total = sum(f[2] for f in self.sample)
        self.total_kcal = str(total)

    def save(self):
        app = App.get_running_app()
        user = app.auth.current_user() or "guest"
        for food in self.sample:
            app.storage.add_food(user, self.meal, food)
        self.manager.current = "home"

class HealthApp(App):
    def build(self):
        Window.clearcolor = (0.078, 0.086, 0.102, 1)
        Window.softinput_mode = "below_target"
        here = os.path.dirname(os.path.abspath(__file__))
        Builder.load_file(os.path.join(here, "screens.kv"))

        db_path = os.path.join(self.user_data_dir, "app.db")
        self.auth = AuthStore(db_path)
        self.storage = Storage(db_path)

        sm = ScreenManager(transition=NoTransition())
        for cls, name in ((LoginScreen, "login"), (PermissionsScreen, "permissions"),
                          (HomeScreen, "home"), (AddFoodScreen, "addfood"),
                          (PhotoScreen, "photo")):
            sm.add_widget(cls(name=name))
        sm.current = self.start_screen() if (self.auth.current_user() or self.is_guest()) else "login"
        return sm

    def is_guest(self):
        return os.path.exists(os.path.join(self.user_data_dir, "guest_mode"))

    def flag_path(self):
        return os.path.join(self.user_data_dir, "permissions_asked")

    def start_screen(self):
        return "home" if os.path.exists(self.flag_path()) else "permissions"

    def enter(self):
        self.root.current = self.start_screen()

if __name__ == "__main__":
    HealthApp().run()