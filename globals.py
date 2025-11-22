# Centralized tuning globals for BalatroPy
# Move critical magic numbers here for easy balance tweaks.

# --- Money / Reward parameters ---
SCORE_TO_MONEY_RATE = 10            # every 10 score -> 1 money
GUARANTEED_BASE_MONEY = 10         # base guaranteed money when target exceeded
CONSOLATION_MONEY = 5              # consolation reward when target not reached
MAX_ROUND_MONEY = 50               # cap per round

# --- Gambit (kill/spare) reward parameters ---
KILL_BONUS_BASE = 5                # starting kill bonus
KILL_BONUS_MULTIPLIER = 2          # consecutive-kill multiplier base

# --- Ante / Difficulty progression ---
ANTE_1_TARGET = 60                 # target score for ante 1
ANTE_INCREMENT_PER_LEVEL = 100     # increase to target per ante level

# Boss health tuning
BOSS_HEALTH_START = 60
BOSS_HEALTH_INCREMENT_PER_ANTE = 100

# --- True Ending thresholds (inclusive) ---
# If the player's `total_spared_bosses` falls within this range when
# confirming a gambit result, the game will route to a TRUE ENDING state.
TRUE_ENDING_MIN_SPARE = 3
TRUE_ENDING_MAX_SPARE = 6

# --- Joker Kill Banner / Penalty Tuning ---
# Every `KILL_BANNER_THRESHOLD` consecutive kills, pick a random active
# joker and mark it with `joker_kill_banner_index` so the UI can render
# a special banner/tooltip for that joker. Set to -1 to indicate none.
joker_kill_banner_index = -1
KILL_BANNER_THRESHOLD = 2


# --- Boss metadata: display names, stories and unique abilities ---
# This dictionary is read by `game.py` when loading a boss for an ante.
BOSS_METADATA = {
	'boss1': {
		'display_name': "Gallus, the Myopic",
		'story': "Dört gözüm var... ama sadece önümdeki yemi görüyorum. Kanatlarım var... ama sadece toz kaldırmak için çırpınıyorum. Boynuzlarım... neden varlar, bilmiyorum. Ben, 'yükselmeye' çalışan bir 'hiç'im. Yükselmeye çalıştım, ama sadece daha gülünç hale geldim. Kaderinden kaçamazsın. Yemini ye ve sonunu bekle.",
		'ability_key': "PECKING",
		'ability_desc': "YETENEK: Eldeki en düşük değerli kart oynanmak zorundadır."
	},
	'boss2': {
		'display_name': "Oculus, the Thousand Eyes",
		'story': "Görüyorum! Her kartı, her olasılığı, her anı... Milyarlarca görüntü. Ama hiçbiri... hiçbiri anlamlı değil. Bu bir lütuf değil, bu bir gürültü! Her şeyi bilmek, hiçbir şeyi bilmemektir. Yalvarırım... gözlerimi kapatmama yardım et. Sadece... sessizlik.",
		'ability_key': "REDUCE_DISCARDS_2",
		'ability_desc': "YETENEK: Bu Ante boyunca -2 Değiştirme Hakkı."
	},
	'mainboss1': {
		'display_name': "Azazel, the First General",
		'story': "Bir zamanlar ordulara hükmederdim. Düşüş emrini ben verdim. Ama... düştüğümüz yer burası değildi. Burası... boş. Ne bir efendi var, ne de bir savaş. Ben, olmayan bir krallığın generali, olmayan bir kanunun yargıcıyım. Gücümün bir ağırlığı yok. Lütfen, bana somut bir şey ver... ölümü bile kabul ederim.",
		'ability_key': "NO_HIGH_CARDS_HELD",
		'ability_desc': "YETENEK: As (A) veya Papaz (K) elde tutulamaz, oynanmalıdır."
	},
	'smug': {
		'display_name': "Smug, the Collector",
		'story': "Heh. Güzel el... Neredeyse benim koleksiyonum kadar iyi. Her şeyi topladım. Paraları, mücevherleri, ruhları... Sonra toplamayı durduramadım. Çürümeye başladığımı fark etmedim. O kadar doluyum ki... içimden taşıyorum. Bu sırıtış (smug) yüzümde dondu kaldı. Al... sen de bir parçamı al. Koleksiyonuma katıl.",
		'ability_key': "MONEY_TAX",
		'ability_desc': "YETENEK: Oynanan her el 1 MONEY çalar (eğer varsa)."
	},
	'shi-shu': {
		'display_name': "Shi-Shu, the Isolated",
		'story': "Yaklaşma! Dikenlerim... onlar ben değildim. Onlar... korkudan büyüdü. Dokunduğum her şeyi kırdım. Sevdiğim her şeyi... incittim. O yüzden artık kimsenin yaklaşmasına izin vermiyorum. Yalnızlık acı veriyor... ama incitmekten daha az.",
		'ability_key': "RECOIL_DAMAGE",
		'ability_desc': "YETENEK: Oynanan her el, oyuncunun mevcut Puanına 10 hasar verir."
	},
	'mainboss2': {
		'display_name': "Al, the Alpha",
		'story': "Sürüm... benim yüzümden kayboldu. Bir lider korumak zorundadır. Ama ben... ben meydan okudum. Gücümün her şeye yeteceğini sanan bir aptaldım. Kibrim, sürümün sonu oldu. Şimdi uluyorum... ama cevap veren tek şey kendi yankım. Lidersiz bir Alfa, hiçtir. Sürüsüz bir kurt... sadece bir hayvandır.",
		'ability_key': "ALPHA_RULE",
		'ability_desc': "YETENEK: Sadece 3 veya daha fazla karttan oluşan eller oynanabilir."
	},
	'pimp': {
		'display_name': "Pimp, the Unseen",
		'story': "(Tatlı bir ciyaklama sesi. Sonra ses değişir, derinleşir.) ...Beni beklemiyordun, değil mi? 'Sadece küçük bir hamster.' 'Sadece bir tur daha.' 'Sadece bir lokma daha.' Durmadım. Tekerlek döndü, ben yedim. Kafesi yedim. Sonra kafesin sahibini yedim. Açgözlülük (Smug) biriktirir. Ben... ben tüketirim. Tıpkı senin gibi.",
		'ability_key': "MINUS_1_HAND_SIZE",
		'ability_desc': "YETENEK: Oburluk! Bu savaş boyunca El Boyutu 1 azalır."
	},
	'coby': {
		'display_name': "Coby, the Corrupted Forest",
		'story': "Orman... sessizdi. Yeşildi. Bu... bu 'oyun' değildi. Bu yer... boynuzlarımı çarpıttı. Toynaklarım sahte zeminlere çarpıyor. Ben, dijital bir kafese hapsedilmiş bir doğa anısıyım. Senin 'gerçek' dünyanı kıskanıyorum. Senin 'gerçek' seçimlerini... Merhamet istemiyorum. Sadece... gerçek rüzgarı hissetmek istiyorum.",
		'ability_key': "JOKER_ENVY",
		'ability_desc': "YETENEK: Bu Ante boyunca rastgele 1 Joker devre dışı bırakılır."
	},
	'mainboss3': {
		'display_name': "Kara, the Architect",
		'story': "Demek geldin. Diğerleriyle tanıştın. Kibir, Korku, Hırs... benim küçük parçalarım. Ve şimdi benimle, Kara'yla tanıştın. Ben, bu yerin mimarıyım. Ben Umutsuzluk'um. Bu kumarhaneyi kendim için inşa ettim. Ve yalnız hissettiğimde... diğerlerini içeri çektim. Seni içeri çektim. Onları Bağışlamanın 'merhamet' olduğunu mu sanıyorsun? Öldürmenin 'güç' olduğunu mu? Fark etmez. Bu 'Ruhun Kumarı'. *Benim* kumarım. Ve sonunda... herkes kaybeder. Şimdi, son anlamsız seçimini yap.",
		'ability_key': "DESPAIR",
		'ability_desc': "YETENEK: Her el oynandıktan sonra, Kalan Değiştirme Hakkı 1 azalır."
	}
	,
	'endless1': {
		'display_name': "Sit The Vampire",
		'story': "...",
		'ability_key': "CONSUME_HAND_1",
		'ability_desc': "YETENEK: Her tur rastgele 1 kartı elden siler."
	},
	'endless2': {
		'display_name': "Sneijk The Reptillian",
		'story': "...",
		'ability_key': "REDUCE_DISCARDS_2",
		'ability_desc': "YETENEK: Bu Ante boyunca -2 Değiştirme Hakkı."
	},
	'endless3': {
		'display_name': "Blood Thirst",
		'story': "...",
		'ability_key': "ALPHA_RULE",
		'ability_desc': "YETENEK: Sadece 3 veya daha fazla karttan oluşan eller oynanabilir."
	},
	'endless4': {
		'display_name': "Three Eye of Demon",
		'story': "...",
		'ability_key': "NO_HIGH_CARDS_HELD",
		'ability_desc': "YETENEK: As (A) veya Papaz (K) elde tutulamaz."
	},
	'endless5': {
		'display_name': "King Shakura",
		'story': "...",
		'ability_key': "MONEY_TAX",
		'ability_desc': "YETENEK: Oynanan her el 1 Para çalar."
	}
}


# --- Boss Dialogues for gambit choices (displayed on boss-defeated screen) ---
# Each boss key maps to an 'opening' line and three options the player chooses from.
# Options contain a label (shown on the button), a type, the spoken text, and a
# short effect description used in the UI.
BOSS_DIALOGUES = {
	'boss1': {
		'opening': "Küçük taneler... bana yetmedi, ama senin elinle yarışırım.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Yemini yedin; şimdi sıra sende!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Neden koştuğunu bana anlat.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bana yem ver, yollarımız ayrılır.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'boss2': {
		'opening': "Gözlerim her şeyi gördü... ama yine de şaşırdım.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Görüntülerini sileceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Gözlerin yorgun görünüyor, sus.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Sana bir perde veririm, görmeyi bırak.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'mainboss1': {
		'opening': "Bir general olarak emrediyorum: artık dinlenebilirim.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Senin son emrin burada!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Emrinden vazgeçmek ister misin?", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bana bir miras bırak, gideyim.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'smug': {
		'opening': "Heh, güzel bir koleksiyon daha. Sen de takas edebilirsin.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Koleksiyonumu parçalayıp götüreceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Neden biriktirdiğini söyle.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir miktar ver, seni serbest bırakayım.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'shi-shu': {
		'opening': "Dokunma... dokunma beni daha da kırar.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Sensiz daha güçlü olurum!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Kesinlikle yalnızsın. Dinleyeyim mi?", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir korunma ver, susacağım.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'mainboss2': {
		'opening': "Bir liderin son sözü üzerinden geçilir... benimki bu.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Sürünü paramparça edeceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Lider olmanın yükünü anlat.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir parça onur verirsen çekilirim.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'pimp': {
		'opening': "Daha fazlası... her zaman daha fazlası.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Tıkanacaksın açgözlülüğünde!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Neden duramıyorsun, anlat.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Biraz bırak, huzura kavuş.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'coby': {
		'opening': "Toprak, kök ve çürüme... hisset beni, sonra bırak.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Ormanı yakacağım, kökleri kurutacağım!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Çaresizliğini duy, birlikte gerek.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir filiz ver, sessiz kalırım.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'mainboss3': {
		'opening': "Ben mimar, bu kumarhane benim tasarımım. Seçim senin son kozun.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Tüm planlarını çökerteceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Beni affetmeye ikna et.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bana pay ver, seni serbest bırakırım.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'endless1': {
		'opening': "Gecenin suskunluğu, açlığımın yankısı.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Seni karanlığa gömeceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Bir parça ışık ver, dururum.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Kanından bir yudum ver, çekilirim.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'endless2': {
		'opening': "Soğuk sürüngen gözlerle bakıyorum; hareket etme.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Deri altına çökeceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Saklanma nedenini anlat.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir parça sıcaklık ver, yoluma bakayım.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'endless3': {
		'opening': "Kanın tadı tutkudur; duramam.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Seni sındıracağım!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Dur, neden susuyorsun?", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir damla ver, çekilebilirim.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'endless4': {
		'opening': "Üç gözümle her açıyı sayıyorum.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Gözcünü kıracağım!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Gözlerinin yükünü paylaşayım mı?", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Görmeyi kesmem için bir hediye ver.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	},
	'endless5': {
		'opening': "Bir kralın son emri: toplayın.",
		'options': [
			{'label': 'YIKIM (Saldır)', 'type': 'AGGRESSIVE', 'text': "Tahtını devireceğim!", 'effect_desc': "Ruhu Tüket (+Para, +Kill)"},
			{'label': 'MERHAMET (Dinle)', 'type': 'EMPATHETIC', 'text': "Çünkü hükmetmek yordu seni, dinlen.", 'effect_desc': "Ruhu Arındır (Savaş Modu, +Spare)"},
			{'label': 'ANLAŞMA (Rüşvet)', 'type': 'RATIONAL', 'text': "Bir ödül ver, yoluna bakayım.", 'effect_desc': "Savaşmadan Geç (+Az Para, +Spare)"}
		]
	}
}

# Canonical boss sequence used for ante 1..9
BOSS_SEQUENCE_KEYS = [
	'boss1', 'boss2', 'mainboss1',
	'smug', 'shi-shu', 'mainboss2',
	'pimp', 'coby', 'mainboss3'
]


# Runtime: current boss ability key (set by game when boss is loaded)
current_boss_ability = None
# Runtime: current boss display name to show as a fixed label above the boss sprite
current_boss_display_name = ""

# New globals for deck/selection and perks
# Maximum number of Joker slots the player can have
JOKER_SLOTS_MAX = 6

# Modifier applied to ante target calculation (float multiplier)
ANTE_TARGET_MODIFIER = 1.0

# Counter for HOLOPITY mechanic (tracked globally)
HOLOPITY_COUNTER = 0

# Selected deck's special perk key (set when player chooses a deck)
SELECTED_DECK_PERK = None

# UI/runtime: which deck index is currently focused in deck-selection screen
current_deck_selection_index = 0

# Persistent unlock table for decks (True = unlocked). Save/load is TODO.
DECK_UNLOCKS = {
	'RED': True,
	'BLUE': True,
	'GOLD': False,
	'GHOST': False,
	'SOUL': False,
	'CHAOS': False,
}

# --- Fate Orbs: predefined pool and player inventory ---
# `FATE_ORBS_POOL` contains canonical fate-orb definitions the game
# can draw from when granting or selling orbs. Each orb is a dict with
# an `id` (used in saved state), `name`, `desc` (shown in UI), and a
# `color` RGB tuple used for simple icon rendering.
FATE_ORBS_POOL = [
	{
		'id': 'CURSED_7',
		'name': "Lanetli 7",
		'desc': "7'liler x7 Puan verir ama oynandığında -1 Değiştirme Hakkı siler.",
		'color': (200, 50, 50),
	},
	{
		'id': 'ACE_KING_BOND',
		'name': "Kral ve As Bağı",
		'desc': "As ve Kral birlikte oynanırsa x4 Puan. Biri oynanırken diğeri de seçilmelidir.",
		'color': (50, 100, 200),
	},
	{
		'id': 'BLOOD_DIAMOND',
		'name': "Kanlı Karo",
		'desc': "Karolar +50 Çip verir ama oynandığında 1$ siler.",
		'color': (180, 30, 30),
	},
]

# Player's current fate-orb inventory (unspent). Max capacity: 5.
player_fate_orbs = []

# IDs of fate orb rules that have been applied permanently to the deck.
# Stored as a list of fate-orb `id` strings.
active_fate_rules = []

# Persistent unlocks save file and helpers
import json
import os

SAVE_FILE = "unlocks.json"

def save_deck_unlocks():
	"""Save only the `DECK_UNLOCKS` dictionary to disk."""
	global DECK_UNLOCKS
	try:
		with open(SAVE_FILE, 'w') as f:
			json.dump(DECK_UNLOCKS, f)
	except Exception as e:
		print(f"HATA: Kilitler kaydedilemedi: {e}")

def load_deck_unlocks():
	"""Load deck unlocks from disk and update the runtime `DECK_UNLOCKS`.

	Only existing keys in the default `DECK_UNLOCKS` are updated; extra
	keys in the file are ignored.
	"""
	global DECK_UNLOCKS
	if os.path.exists(SAVE_FILE):
		try:
			with open(SAVE_FILE, 'r') as f:
				loaded_unlocks = json.load(f)
				for key in list(DECK_UNLOCKS.keys()):
					if key in loaded_unlocks:
						DECK_UNLOCKS[key] = bool(loaded_unlocks[key])
		except Exception as e:
			print(f"HATA: Kilitler yüklenemedi: {e}")


	# Ensure every boss metadata entry has a non-empty 'story' string so the
	# boss-defeated narrative screen never encounters an empty story. This is a
	# defensive fix: if a story is missing in the static table, fill with a
	# minimal placeholder so the UI still shows something.
	try:
		for _k, _v in list(BOSS_METADATA.items()):
			try:
				if not isinstance(BOSS_METADATA[_k], dict):
					continue
				s = BOSS_METADATA[_k].get('story') if BOSS_METADATA[_k] is not None else None
				if not s:
					BOSS_METADATA[_k]['story'] = "Hikaye mevcut değil."
			except Exception:
				try:
					BOSS_METADATA[_k] = BOSS_METADATA.get(_k, {}) or {}
					BOSS_METADATA[_k]['story'] = "Hikaye mevcut değil."
				except Exception:
					pass
	except Exception:
		pass
