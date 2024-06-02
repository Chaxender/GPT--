import wx
import wx.lib.scrolledpanel as scrolled
import json
import difflib
import random
from googletrans import Translator
import requests
from bs4 import BeautifulSoup
import os


# Veritabanını yükleme fonksiyonu
def load_database(filename="./messages/database.json"):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def search_and_add_info(user_input, database, translator, target_language):
    translated_input = translator.translate(user_input, src=target_language, dest='tr').text
    closest_match = find_closest_match(translated_input, database)
    if closest_match:
        responses = database[closest_match]
        response = random.choice(responses)
        response_translated = translator.translate(response, src='tr', dest=target_language).text
        return response_translated
    else:
        # Wikipedia'da arama yapma
        search_query = f"site:wikipedia.org {user_input}"
        search_url = f"https://www.google.com/search?q={search_query}"
        response = requests.get(search_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            result_div = soup.find_all('div', class_='BNeawe s3v9rd AP7Wnd')
            if result_div:
                result_text = result_div[0].get_text()
                translated_result = translator.translate(result_text, src='tr', dest=target_language).text
                return translated_result
            else:
                return "Bilgi bulunamadı."
        else:
            return "Arama işlemi başarısız oldu."


# Veritabanını kaydetme fonksiyonu
def save_database(database, filename="database.json"):
    with open(filename, "w") as file:
        json.dump(database, file, indent=4, ensure_ascii=False)


# Belirli bir sohbeti kaydetme fonksiyonu
def save_chat(chat, filename):
    with open(filename, "w", encoding='utf-8') as file:
        json.dump(chat, file, indent=4, ensure_ascii=False)

# Belirli bir sohbeti yükleme fonksiyonu
def load_chat(filename):
    try:
        with open(filename, "r", encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []


# Tüm sohbetleri yükleme fonksiyonu
def load_all_chats(folder="chats"):
    chat_files = []
    if not os.path.exists(folder):
        os.makedirs(folder)
    for file in os.listdir(folder):
        if file.endswith(".json"):
            chat_files.append(file)
    return chat_files


# En yakın eşleşmeyi bulma fonksiyonu
def find_closest_match(user_input, database):
    closest_match = difflib.get_close_matches(user_input, database.keys(), n=1, cutoff=0.6)
    return closest_match[0] if closest_match else None


# Ana çerçeve sınıfı
class ChatBotFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(ChatBotFrame, self).__init__(*args, **kw)
        self.SetIcon(wx.Icon('ico/icon.ico', wx.BITMAP_TYPE_ICO))  # 'icon.ico' dosya adınızı ve yolunuzu buraya ekleyin
        self.Center()
        self.Show(True)
        self.InitUI()
        self.database = load_database()
        self.translator = Translator()
        self.current_language = 'en'
        self.chat_folder = "chats"
        self.chat_files = load_all_chats(self.chat_folder)
        self.current_chat_file = None
        self.UpdateChatHistory()

    def InitUI(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        langMenu = wx.Menu()

        fileItem = fileMenu.Append(wx.ID_EXIT, 'Çıkış', 'Uygulamayı kapat')
        self.Bind(wx.EVT_MENU, self.OnQuit, fileItem)

        languages = ['en', 'es', 'fr', 'de', 'it', 'tr']
        for lang in languages:
            langItem = langMenu.Append(wx.ID_ANY, lang.upper(), f'{lang.upper()} diline geç')
            self.Bind(wx.EVT_MENU, self.OnChangeLanguage, langItem)

        menubar.Append(fileMenu, '&Dosya')
        menubar.Append(langMenu, '&Diller')

        self.SetMenuBar(menubar)

        splitter = wx.SplitterWindow(self)
        self.panel = wx.Panel(splitter)
        self.sidebar = wx.Panel(splitter, style=wx.BORDER_SUNKEN)

        # Sohbet geçmişi için TreeCtrl
        self.tree = wx.TreeCtrl(self.sidebar)
        self.root = self.tree.AddRoot("Sohbet Geçmişi")
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelectChat, self.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClick, self.tree)

        # Yeni sohbet butonu
        new_chat_button = wx.Button(self.sidebar, label="Yeni Sohbet")
        new_chat_button.Bind(wx.EVT_BUTTON, self.OnNewChat)

        sidebar_sizer = wx.BoxSizer(wx.VERTICAL)
        sidebar_sizer.Add(new_chat_button, 0, wx.EXPAND | wx.ALL, 5)
        sidebar_sizer.Add(self.tree, 1, wx.EXPAND)
        self.sidebar.SetSizer(sidebar_sizer)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # Kaydırılabilir panel
        self.chat_panel = scrolled.ScrolledPanel(self.panel, style=wx.VSCROLL)
        self.chat_panel.SetupScrolling()
        self.chat_sizer = wx.BoxSizer(wx.VERTICAL)
        self.chat_panel.SetSizer(self.chat_sizer)

        vbox.Add(self.chat_panel, proportion=1, flag=wx.EXPAND | wx.ALL, border=10)

        # Girdi alanı ve gönder düğmesi
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.entry = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.entry.Bind(wx.EVT_TEXT_ENTER, self.OnSend)
        hbox.Add(self.entry, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        send_button = wx.Button(self.panel, label="Gönder", style=wx.BORDER_NONE)
        send_button.SetBackgroundColour(wx.Colour(52, 152, 219))
        send_button.SetForegroundColour(wx.Colour(255, 255, 255))
        send_button.Bind(wx.EVT_BUTTON, self.OnSend)
        hbox.Add(send_button, flag=wx.ALL, border=5)

        vbox.Add(hbox, flag=wx.EXPAND | wx.ALL, border=10)

        self.panel.SetSizer(vbox)

        splitter.SplitVertically(self.sidebar, self.panel, 200)
        self.SetTitle("Gpd-i")
        self.SetSize((900, 600))
        self.Centre()

    def OnQuit(self, event):
        self.Close()

    def OnChangeLanguage(self, event):
        lang_id = event.GetId()
        item = self.GetMenuBar().FindItemById(lang_id)
        new_language = item.GetItemLabel().lower()

        if new_language != self.current_language:
            self.current_language = new_language

            # Arayüzdeki metinleri çevirme işlemi
            self.TranslateUI(new_language)

            # Bardaki metinleri de çevirme işlemi
            self.TranslateBar(new_language)

            wx.MessageBox(f"Dil {item.GetItemLabel()} olarak değiştirildi.", "Bilgi", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"Zaten {item.GetItemLabel()} dili seçili.", "Uyarı", wx.OK | wx.ICON_WARNING)

    def TranslateUI(self, target_language):
        # Arayüz metinlerini çevirme işlemi
        self.SetTitle(self.translator.translate("Gpd-i", src='tr', dest=target_language).text)
        self.entry.SetHint(self.translator.translate("Type here...", src='tr', dest=target_language).text)

        # Menü metinlerini güncelleme işlemi
        menubar = self.GetMenuBar()
        langMenu = menubar.GetMenu(1)  # Dil menüsü

        languages = ['en', 'es', 'fr', 'de', 'it', 'tr']
        for idx in range(langMenu.GetMenuItemCount()):
            langItem = langMenu.FindItemByPosition(idx)
            langItem.SetItemLabel(languages[idx].upper())

        self.Refresh()

    def TranslateBar(self, target_language):
        menubar = self.GetMenuBar()
        fileMenu = menubar.GetMenu(0)
        langMenu = menubar.GetMenu(1)

        # File menüsündeki metinleri çevir
        for idx in range(fileMenu.GetMenuItemCount()):
            menu_item = fileMenu.FindItemByPosition(idx)
            if menu_item:
                label = menu_item.GetLabel()
                translated_label = self.translator.translate(label, src='tr', dest=target_language).text
                menu_item.SetItemLabel(translated_label)

        # Language menüsündeki metinleri çevir
        for idx in range(langMenu.GetMenuItemCount()):
            menu_item = langMenu.FindItemByPosition(idx)
            if menu_item:
                label = menu_item.GetLabel()
                translated_label = self.translator.translate(label, src='tr', dest=target_language).text
                menu_item.SetItemLabel(translated_label)

        self.Refresh()

    def OnSend(self, event):
        user_input = self.entry.GetValue().strip()
        if user_input == "":
            return

        self.AddMessage("Sen", user_input, wx.Colour(52, 152, 219), is_user=True)
        self.entry.SetValue("")

        response = search_and_add_info(user_input, self.database, self.translator, self.current_language)
        if response:
            self.AddMessage("Gpd-i", response, wx.Colour(231, 76, 60))
        else:
            self.AddMessage("Gpd-i",
                            "Bu soruya nasıl cevap vereceğimi bilmiyorum. Lütfen bana nasıl cevap vereceğimi öğret.",
                            wx.Colour(231, 76, 60))
            new_response = wx.GetTextFromUser("Bu soruya nasıl cevap vermeliyim?", "Cevap Öğret")
            if new_response:
                translated_user_input = self.translator.translate(user_input, src=self.current_language, dest='tr').text
                translated_new_response = self.translator.translate(new_response, src=self.current_language,
                                                                    dest='tr').text
                if translated_user_input in self.database:
                    self.database[translated_user_input].append(translated_new_response)
                else:
                    self.database[translated_user_input] = [translated_new_response]
                save_database(self.database)
                self.AddMessage("Gpd-i", "Teşekkürler! Şimdi öğrendim.", wx.Colour(231, 76, 60))

        # Sohbet geçmişine ekle
        if self.current_chat_file:
            chat = load_chat(self.current_chat_file)
            chat.append((user_input, response))
            save_chat(chat, self.current_chat_file)
        else:
            new_chat_filename = os.path.join(self.chat_folder, f"chat_{len(self.chat_files) + 1}.json")
            self.chat_files.append(new_chat_filename)
            self.current_chat_file = new_chat_filename
            save_chat([(user_input, response)], self.current_chat_file)

        self.UpdateChatHistory()

    def AddMessage(self, sender, message, color, is_user=False):
        message_text = f"{sender}: {message}"
        message_panel = wx.Panel(self.chat_panel)
        message_sizer = wx.BoxSizer(wx.HORIZONTAL)
        message_panel.SetSizer(message_sizer)

        if is_user:
            message_sizer.AddStretchSpacer()

        bubble = wx.StaticText(message_panel, label=message_text, style=wx.ALIGN_LEFT | wx.ST_ELLIPSIZE_END)
        bubble.SetBackgroundColour(color)
        bubble.SetForegroundColour(wx.Colour(255, 255, 255))
        bubble.SetWindowStyle(wx.BORDER_RAISED)
        bubble.Wrap(400)
        message_sizer.Add(bubble, flag=wx.ALL, border=5)

        if not is_user:
            message_sizer.AddStretchSpacer()

        self.chat_sizer.Add(message_panel, flag=wx.EXPAND | wx.ALL, border=5)
        self.chat_panel.Layout()
        self.chat_panel.SetupScrolling(scrollToTop=False)

    def UpdateChatHistory(self):
        self.tree.DeleteChildren(self.root)
        for chat_file in self.chat_files:
            chat_name = os.path.basename(chat_file).replace('.json', '')
            item = self.tree.AppendItem(self.root, chat_name)
        self.tree.ExpandAll()

    def OnSelectChat(self, event):
        item = event.GetItem()
        if item:
            item_text = self.tree.GetItemText(item)
            chat_file = os.path.join(self.chat_folder, f"{item_text}.json")
            self.DisplayChatHistory(chat_file)

    def DisplayChatHistory(self, chat_file):
        self.current_chat_file = chat_file
        self.chat_sizer.Clear(True)
        chat = load_chat(chat_file)
        for user_input, response in chat:
            self.AddMessage("Sen", user_input, wx.Colour(52, 152, 219), is_user=True)
            self.AddMessage("Gpd-i", response, wx.Colour(231, 76, 60))

    def OnRightClick(self, event):
        item = event.GetItem()
        if item:
            self.tree.SelectItem(item)
            menu = wx.Menu()
            delete_item = menu.Append(wx.ID_ANY, "Sil")
            self.Bind(wx.EVT_MENU, lambda evt, item=item: self.OnDeleteChat(item), delete_item)
            self.PopupMenu(menu)
            menu.Destroy()

    def OnDeleteChat(self, item):
        item_text = self.tree.GetItemText(item)
        chat_file = os.path.join(self.chat_folder, f"{item_text}.json")
        if os.path.exists(chat_file):
            os.remove(chat_file)
            self.chat_files.remove(chat_file)
        self.UpdateChatHistory()
        self.chat_sizer.Clear(True)
        self.chat_panel.Layout()
        self.current_chat_file = None

    def OnNewChat(self, event):
        self.current_chat_file = None
        self.chat_sizer.Clear(True)
        self.chat_panel.Layout()


# Ana uygulama sınıfı
class ChatBotApp(wx.App):
    def OnInit(self):
        self.frame = ChatBotFrame(None)
        self.frame.Show()
        return True


if __name__ == "__main__":
    app = ChatBotApp()
    app.MainLoop()
