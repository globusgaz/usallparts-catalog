#!/usr/bin/env python3
import os
import csv
import sys
import urllib.request
import xml.etree.ElementTree as ET
from io import StringIO
from datetime import datetime

SHEET_URL = "https://docs.google.com/spreadsheets/d/1gq1c4L2TEyRmxNpbRGHJdSNYtd2FNgOMi9-a1CX5ZDQ/export?format=csv&gid=401593410"
OUT_FILE = "USAllParts.yml"

def sanitize_text(text):
    if not text:
        return ""
    return str(text).strip()

def load_categories():
    categories = {
        "1": "Автозапчастини та комплектуючі"
    }
    print(f"📋 Створено {len(categories)} категорію: 'Автозапчастини та комплектуючі'")
    return categories

def load_products(url, categories):
    print(f"📦 Завантажую товари з Google Sheets...")
    with urllib.request.urlopen(url) as r: 
        txt = r.read().decode("utf-8", errors="ignore")
    rows = list(csv.reader(StringIO(txt)))
    if not rows:
        return []
    
    headers = [h.strip().lower() for h in rows]
    print(f"📋 Заголовки: {headers}")
    
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
    i_price = idx("ціна в uah","price_uah","ціна в uah", d=9)
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
        except Exception:
            qty = 0
        ps = sanitize_text(r[i_price])
        try: 
            clean_price = ps.replace("грн.", "").replace(" ", "").replace("\xa0", "").replace(",", ".")
            price = float(clean_price) if clean_price else None
        except Exception: 
            price = None
        currency = "UAH"
        av = sanitize_text(r[i_presence]).lower()
        presence = (av in ["true","1","yes","в наявності","наявний","+"]) or (qty > 0)
        category_id = "1"
        if not code or not name or price is None: 
            skipped += 1
            continue
        name_with_code = f"{code} {name}" if code not in name.upper() else name
        products.append({
            "id": f"f0_{code}",
            "name": name_with_code,
            "price": price,
            "currency": currency or "UAH",
            "description": name_with_code,
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
    root = ET.Element('yml_catalog')
    root.set('date', datetime.now().strftime('%Y-%m-%d %H:%M'))
    shop = ET.SubElement(root, 'shop')
    name = ET.SubElement(shop, 'name')
    name.text = 'USAllParts'
    company = ET.SubElement(shop, 'company')
    company.text = 'USAllParts'
    url = ET.SubElement(shop, 'url')
    url.text = 'https://example.com'
    currencies = ET.SubElement(shop, 'currencies')
    ET.SubElement(currencies, 'currency', id='UAH', rate='1')
    ET.SubElement(currencies, 'currency', id='USD', rate='38')
    categories_elem = ET.SubElement(shop, 'categories')
    for cat_id, cat_name in categories.items():
        ET.SubElement(categories_elem, 'category', id=cat_id).text = cat_name
    offers = ET.SubElement(shop, 'offers')
    for p in products:
        offer = ET.SubElement(offers, 'offer')
        offer.set('id', str(p['id']))
        offer.set('available', 'true' if p['presence'] else 'false')
        name = ET.SubElement(offer, 'name')
        name.text = p['name']
        price = ET.SubElement(offer, 'price')
        price.text = str(p['price'])
        currency = ET.SubElement(offer, 'currencyId')
        currency.text = p['currency']
        category = ET.SubElement(offer, 'categoryId')
        category.text = p['category_id']
        vendor = ET.SubElement(offer, 'vendor')
        vendor.text = p['vendor']
        vendor_code = ET.SubElement(offer, 'vendorCode')
        vendor_code.text = p['vendor_code']
        # Додаємо параметри Prom.ua/TecDoc
        param_brand = ET.SubElement(offer, 'param', name="Виробник")
        param_brand.text = p['vendor']
        param_code = ET.SubElement(offer, 'param', name="Код запчастини")
        param_code.text = p['vendor_code']
        stock_quantity = ET.SubElement(offer, 'stock_quantity')
        stock_quantity.text = str(p['quantity'])
        description = ET.SubElement(offer, 'description')
        description.text = p['description']
        for pic in p['pictures']:
            picture = ET.SubElement(offer, 'picture')
            picture.text = pic
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"🎉 Згенеровано {filename} з {len(products)} товарами та {len(categories)} категоріями")

def main():
    print("🚀 Генератор USAllParts YML")
    print("=" * 40)
    categories = load_categories()
    products = load_products(SHEET_URL, categories)
    if not products:
        print("❌ Не знайдено товарів")
        sys.exit(1)
    print(f"🔍 Діагностика першого товару:")
    if products:
        first = products
        print(f"  Назва: '{first['name']}'")
        print(f"  Ціна: {first['price']}")
        print(f"  Валюта: {first['currency']}")
        print(f"  Виробник: {first['vendor']}")
        print(f"  Код запчастини: {first['vendor_code']}")
    write_yml(products, categories, OUT_FILE)

if __name__ == "__main__":
    main()
