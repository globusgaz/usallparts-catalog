#!/usr/bin/env python3
import os, csv, sys, urllib.request, xml.etree.ElementTree as ET
from io import StringIO
CSV_URL = os.getenv("MY_PRODUCTS_SHEET_URL","").strip()
OUT_FILE = "USAllParts.yml"
def sz(x): return (x or "").strip()
def load(url):
    with urllib.request.urlopen(url) as r: txt=r.read().decode("utf-8",errors="ignore")
    rows=list(csv.reader(StringIO(txt))); 
    if not rows: return []
    hdr=[h.strip().lower() for h in rows[0]]
    def idx(*names, d=None):
        s={n.lower() for n in names}; 
        for i,h in enumerate(hdr):
            if h in s: return i
        return d
    i_code=idx("номер частини","код","артикул","code","vendor_code",d=0)
    i_vendor=idx("виробник","бренд","vendor","manufacturer",d=1)
    i_name=idx("назва частини","назва","name","title",d=2)
    i_ph=idx("фото","photos","pictures","images",d=3)
    i_qty=idx("к-ть","кількість","quantity","qty",d=4)
    i_price=idx("ціна","price",d=5)
    i_curr=idx("код валюти","валюта","currency",d=6)
    i_av=idx("наявність","availability","available","is_available",d=7)
    need=max(i_code,i_vendor,i_name,i_ph,i_qty,i_price,i_curr,i_av)
    items=[]
    for r in rows[1:]:
        if len(r)<=need: r+=[""]*(need-len(r)+1)
        code=sz(r[i_code]); name=sz(r[i_name]); vendor=sz(r[i_vendor]) or "USAllParts"
        ph_raw=sz(r[i_ph]); pics=[p.strip() for p in ph_raw.replace("\n"," ").replace("|",",").split(",") if p.strip()][:10]
        try: qty=int(float(sz(r[i_qty]) or "0"))
        except: qty=0
        ps=sz(r[i_price]).replace(",", "."); 
        try: price=float(ps) if ps else None
        except: price=None
        cur_raw=sz(r[i_curr]) or "30"
        curr="UAH" if cur_raw=="30" else ("USD" if cur_raw=="840" else cur_raw.upper())
        av=sz(r[i_av]).lower()
        presence = (av in ["true","1","yes","в наявності","наявний","+"]) or (qty>0)
        if not code or not name or price is None: continue
        items.append({"id":f"my_{code}","name":name,"price":price,"currency":curr or "UAH",
                      "description":name,"presence":presence,"quantity": qty if presence else 0,
                      "pictures":pics,"category_id":"0","vendor":vendor,"vendor_code":code})
    return items
def write_yml(products, fn):
    root=ET.Element("yml_catalog",attrib={"date": ""}); shop=ET.SubElement(root,"shop")
    ET.SubElement(shop,"name").text="USAllParts"; ET.SubElement(shop,"company").text="USAllParts"; ET.SubElement(shop,"url").text="https://example.com"
    cur=ET.SubElement(shop,"currencies"); ET.SubElement(cur,"currency",attrib={"id":"UAH","rate":"1"}); ET.SubElement(cur,"currency",attrib={"id":"USD","rate":"38"})
    cats=ET.SubElement(shop,"categories"); ET.SubElement(cats,"category",attrib={"id":"0"}).text="Без категорії"
    offers=ET.SubElement(shop,"offers")
    for p in products:
        o=ET.SubElement(offers,"offer",attrib={"id":p["id"]})
        ET.SubElement(o,"name").text=p["name"]; ET.SubElement(o,"price").text=str(p["price"]); ET.SubElement(o,"currencyId").text=(p["currency"] or "UAH").upper()
        ET.SubElement(o,"categoryId").text=p["category_id"]; ET.SubElement(o,"vendor").text=p["vendor"]; ET.SubElement(o,"vendorCode").text=p["vendor_code"]
        ET.SubElement(o,"available").text="true" if p["presence"] else "false"; ET.SubElement(o,"stock_quantity").text=str(p["quantity"]); ET.SubElement(o,"description").text=p["description"]
        for pic in p["pictures"]: ET.SubElement(o,"picture").text=pic
    ET.ElementTree(root).write(fn,encoding="utf-8",xml_declaration=True)
def main():
    if not CSV_URL: print("No MY_PRODUCTS_SHEET_URL"); sys.exit(1)
    prods=load(CSV_URL); write_yml(prods, OUT_FILE); print(f"Wrote {OUT_FILE}: {len(prods)}")
if __name__=="__main__": main()
