#!/usr/bin/env python3
import os, csv, sys, urllib.request, xml.etree.ElementTree as ET
from io import StringIO
from datetime import datetime

# Фіксовані URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gq1c4L2TEyRmxNpbRGHJdSNYtd2FNgOMi9-a1CX5ZDQ/export?format=csv&gid=401593410"
CATEGORIES_URL = "https://docs.google.com/spreadsheets/d/1GqFHdi5-5YszbgyubWNQUwbAsLATikK47V80vtu5WhA/export?format=csv"
OUT_FILE = "USAllParts.yml"

def sanitize_text(text):
    if not text:
        return ""
    return str(text).strip()

def load_categories():
    """Завантажуємо категорії з USAllParts таблиці"""
    try:
        print(f"📁 Завантажую категорії з Google Sheets...")
        with urllib.request.urlopen(CATEGORIES_URL) as r: 
            txt = r.read().decode("utf-8", errors="ignore")
        rows = list(csv.reader(StringIO(txt)))
        if not rows: 
            return {"0": "Автозапчастини"}
        
        categories = {"0": "Автозапчастини"}  # Базова категорія
        headers = [h.strip().lower() for h in rows[0]]
        
        # Шукаємо колонки з категоріями
        def idx(*names, d=None):
            s = {n.lower() for n in names}
            for i, h in enumerate(headers):
                if h in s: 
                    return i
            return d
        
        i_category = idx("категорія", "category", "тип", "type", "група", "group", d=1)
        
        for r in rows[1:]:
            if len(r) > i_category and r[i_category]:
                cat_name = sanitize_text(r[i_category])
                if cat_name and cat_name not in categories.values():
                    cat_id = str(len(categories))
                    categories[cat_id] = cat_name
        
        print(f"📋 Завантажено {len(categories)} категорій")
        return categories
        
    except Exception as e:
        print(f"⚠️ Помилка завантаження категорій: {e}")
        return {"0": "Автозапчастини"}

def load_products(url, categories):
    print(f"📦 Завантажую товари з Google Sheets...")
    with urllib.request.urlopen(url) as r: 
        txt = r.read().decode("utf-8", errors="ignore")
    rows = list(csv.reader(StringIO(txt)))
    if not rows: 
        return []
    
    headers = [h.strip().lower() for h in rows[0]]
    print(f"📋 Заголовки: {headers[:8]}...")
    
    def idx(*names, d=None):
        s = {n.lower() for n in names}
        for i, h in enumerate(headers):
            if h in s: 
                return i
        return d
    
    i_code = idx("номер частини","код","артикул","code","vendor_code", d=0)
    i_vendor = idx("виробник","бренд","vendor","manufacturer", d=1)
    i_name = idx("назва частини","назва","name","title", d=2)
    i_photos = idx("фото","photos","pictures","images", d=3)
    i_qty = idx("к-ть","кількість","quantity","qty", d=4)
    i_price = idx("ціна","price", d=5)
    i_curr = idx("код валюти","валюта","currency", d=6)
    i_presence = idx("наявність","availability","available","is_available", d=7)
    i_category = idx("категорія","category","тип","type","група","group", d=8)
    
    need = max(i_code, i_vendor, i_name, i_photos, i_qty, i_price, i_curr, i_presence, i_category)
    products = []
    loaded = 0
    skipped = 0
    
    for r in rows[1:]:
        if len(r) <= need: 
            r += [""] * (need - len(r) + 1)
        
        code = sanitize_text(r[i_code])
        name = sanitize_text(r[i_name])
        vendor = sanitize_text(r[i_vendor]) or "USAllParts"
        
        photos_raw = sanitize_text(r[i_photos])
        pics = [p.strip() for p in photos_raw.replace("\n"," ").replace("|",",").split(",") if p.strip()][:10]
        
        try: 
            qty = int(float(sanitize_text(r[i_qty]) or "0"))
        except: 
            qty = 0
        
        ps = sanitize_text(r[i_price]).replace(",", ".")
        try: 
            price = float(ps) if ps else None
        except: 
            price = None
        
        curr_raw = sanitize_text(r[i_curr]) or "30"
        currency = "UAH" if curr_raw == "30" else ("USD" if curr_raw == "840" else curr_raw.upper())
        
        av = sanitize_text(r[i_presence]).lower()
        presence = (av in ["true","1","yes","в наявності","наявний","+"]) or (qty > 0)
        
        # Категорія товару
        product_category = sanitize_text(r[i_category]) if i_category < len(r) else ""
        category_id = "0"  # За замовчуванням
        for cat_id, cat_name in categories.items():
            if product_category and product_category.lower() in cat_name.lower():
                category_id = cat_id
                break
        
        if not code or not name or price is None: 
            skipped += 1
            continue
        
        products.append({
            "id": f"my_{code}",
            "name": name,
            "price": price,
            "currency": currency or "UAH",
            "description": name,
            "presence": presence,
            "quantity": qty if presence else 0,
            "pictures": pics,
            "category_id": category_id,
            "vendor": vendor,
            "vendor_code": code
        })
        loaded += 1
    
    print(f"✅ Завантажено: {loaded} товарів")
    print(f"⚠️ Пропущено: {skipped}")
    available = sum(1 for p in products if p['presence'])
    print(f"📊 В наявності: {available}/{loaded}")
    
    return products

def write_yml(products, categories, filename):
    print(f"📝 Генерую YML файл...")
    
    # Створюємо XML структуру
    root = ET.Element('yml_catalog')
    root.set('date', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    shop = ET.SubElement(root, 'shop')
    
    # Основна інформація про магазин
    name = ET.SubElement(shop, 'name')
    name.text = 'USAllParts'
    
    company = ET.SubElement(shop, 'company')
    company.text = 'USAllParts'
    
    url = ET.SubElement(shop, 'url')
    url.text = 'https://example.com'
    
    # Валюты
    currencies = ET.SubElement(shop, 'currencies')
    ET.SubElement(currencies, 'currency', id='UAH', rate='1')
    ET.SubElement(currencies, 'currency', id='USD', rate='38')
    
    # Категорії
    categories_elem = ET.SubElement(shop, 'categories')
    for cat_id, cat_name in categories.items():
        ET.SubElement(categories_elem, 'category', id=cat_id).text = cat_name
    
    # Товари
    offers = ET.SubElement(shop, 'offers')
    
    for p in products:
        offer = ET.SubElement(offers, 'offer')
        offer.set('id', str(p['id']))
        offer.set('available', 'true' if p['presence'] else 'false')
        
        # Основна інформація
        name = ET.SubElement(offer, 'name')
        name.text = p['name']
        
        price = ET.SubElement(offer, 'price')
        price.text = str(p['price'])
        
        currency = ET.SubElement(offer, 'currencyId')
        currency.text = p['currency']
        
        category = ET.SubElement(offer, 'categoryId')
        category.text = p['category_id']
        
        # Виробник
        vendor = ET.SubElement(offer, 'vendor')
        vendor.text = p['vendor']
        
        vendor_code = ET.SubElement(offer, 'vendorCode')
        vendor_code.text = p['vendor_code']
        
        # Кількість
        stock_quantity = ET.SubElement(offer, 'stock_quantity')
        stock_quantity.text = str(p['quantity'])
        
        # Опис
        description = ET.SubElement(offer, 'description')
        description.text = p['description']
        
        # Фото
        for pic in p['pictures']:
            picture = ET.SubElement(offer, 'picture')
            picture.text = pic
    
    # Зберігаємо XML з правильним форматуванням
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    
    print(f"🎉 Згенеровано {filename} з {len(products)} товарами та {len(categories)} категоріями")

def main():
    print("🚀 Генератор USAllParts YML")
    print("=" * 40)
    
    # Завантажуємо категорії
    categories = load_categories()
    
    # Завантажуємо товари
    products = load_products(SHEET_URL, categories)
    if not products:
        print("❌ Не знайдено товарів")
        sys.exit(1)
    
    # Генеруємо YML
    write_yml(products, categories, OUT_FILE)

if __name__ == "__main__":
    main()
