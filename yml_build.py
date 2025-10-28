#!/usr/bin/env python3
import os, csv, sys, urllib.request, xml.etree.ElementTree as ET
from io import StringIO
from datetime import datetime

CSV_URL = os.getenv("MY_PRODUCTS_SHEET_URL","").strip()
OUT_FILE = "USAllParts.yml"

def sanitize_text(text):
    if not text:
        return ""
    return str(text).strip()

def load_products(url):
    with urllib.request.urlopen(url) as r: 
        txt = r.read().decode("utf-8", errors="ignore")
    rows = list(csv.reader(StringIO(txt)))
    if not rows: 
        return []
    
    headers = [h.strip().lower() for h in rows[0]]
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
    
    need = max(i_code, i_vendor, i_name, i_photos, i_qty, i_price, i_curr, i_presence)
    products = []
    
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
        
        if not code or not name or price is None: 
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
            "category_id": "0",
            "vendor": vendor,
            "vendor_code": code
        })
    
    return products

def write_yml(products, filename):
    # Створюємо XML структуру як у основному коді
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
    categories = ET.SubElement(shop, 'categories')
    ET.SubElement(categories, 'category', id='0').text = 'Автозапчастини'
    
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
    
    print(f"✅ Згенеровано {filename} з {len(products)} товарами")

def main():
    if not CSV_URL: 
        print("❌ No MY_PRODUCTS_SHEET_URL")
        sys.exit(1)
    
    products = load_products(CSV_URL)
    write_yml(products, OUT_FILE)

if __name__ == "__main__":
    main()
