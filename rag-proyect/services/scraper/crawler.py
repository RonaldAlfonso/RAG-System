import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
import json
import re
import os
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


PAISES_LATAM = [
    "mexico", "guatemala", "belize", "honduras", "el-salvador", "nicaragua",
    "costa-rica", "panama", "colombia", "venezuela", "ecuador", "peru",
    "bolivia", "chile", "argentina", "uruguay", "paraguay", "brasil",
    "brazil", "cuba", "jamaica", "haiti", "republica-dominicana",
    "puerto-rico", "trinidad-and-tobago",
]

KEYWORDS_TURISMO = [
    "hotel", "hostal", "hostel", "alojamiento", "hospedaje",
    "itinerario", "que hacer", "qué hacer", "atracciones",
    "destino", "turismo", "viaje", "viajero", "tour",
    "presupuesto", "costo", "precio", "tarifa",
    "restaurante", "gastronomia", "gastronomía",
    "playa", "montaña", "selva", "ciudad",
]

CATEGORIAS = {
    "hotel":       ["hotel", "hostal", "hostel", "alojamiento", "hospedaje", "lodge"],
    "destino":     ["destino", "atracciones", "que hacer", "qué hacer", "lugares", "sitios"],
    "itinerario":  ["itinerario", "dias", "días", "ruta", "recorrido", "viaje de"],
    "presupuesto": ["presupuesto", "costo", "precio", "tarifa", "barato", "economico"],
    "gastronomia": ["restaurante", "comida", "gastronomia", "gastronomía", "cocina"],
}

r2=boto3.client("s3",
                endpoint_url=os.getenv("B2_ENDPOINT"),
                aws_access_key_id=os.getenv("B2_KEY_ID"),
                aws_secret_access_key=os.getenv("B2_APP_KEY"),
                region_name="auto")

R2_BUCKET=os.getenv("B2_BUCKET_NAME","turismo-latam-raw")

def r2_upload_file(file_name:str,content:str):
    try:
        r2.put_object(Bucket=R2_BUCKET, Key=f"raw/{file_name}", 
                      Body=content.encode("utf-8"),
                      content_type="application/json")
        return True
    except ClientError as e:
        print(f"Error uploading {file_name} to R2: {e}")
        return False


def contry_detection(url:str,texto:str) -> str:
    for pais in PAISES_LATAM:
        if pais in url.lower() or pais in texto.lower():
            return pais.replace("-", " ").title()
    return "Desconocido"  

def category_detection(texto:str) -> str:
    texto_lower = texto.lower()
    count={cat:0 for cat in CATEGORIAS.keys()}
    for categoria, keywords in CATEGORIAS.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', texto_lower):
                count[categoria] += 1
    if not count:
        return "general"
    return max(count, key=count.get)

def price_detection(texto:str) -> str:
    texto_lower = texto.lower()
    if re.search(r'\b(barato|economico|low[-\s]?cost|budget)\b', texto_lower):
        return "economico"
    elif re.search(r'\b(caro|lujoso|luxury|premium)\b', texto_lower):
        return "lujoso"
    else:
        return "medio"
    
def is_relevant(url:str,texto:str="") -> bool:
    url_lower = url.lower()
    # Descarta URLs claramente irrelevantes
    descartar = ["/talk:", "/user:", "/special:", "/file:", "/template:",
                 "/category:", "/help:", "/wikipedia:", "/mediawiki:"]
    if any(p in url_lower for p in descartar):
        return False
    # Requiere al menos un país de Latam en la URL O keywords en el texto
    tiene_pais = any(p in url_lower for p in PAISES_LATAM)
    tiene_keyword = any(k in texto.lower() for k in KEYWORDS_TURISMO) if texto else False
    return tiene_pais or tiene_keyword

def clean_text(html:str) -> str:
    soup=BeautifulSoup(html, "html.parser")

    for tab in soup(["style", "script", "nav", "footer","header","form","button","aside", "meta", "iframe"]):
        tab.decompose(  )
    text=soup.get_text(separator="\n")
    lineas=[line.strip() for line in text.splitlines()] 
    lineas=[linea for linea in lineas if len(linea)>20]
    return "\n".join(lineas)


class WikivoyageSpider(scrapy.Spider):
    name = "wikivoyage"
    allowed_domains = ["es.wikivoyage.org"]
    start_urls = [ "https://es.wikivoyage.org/wiki/Am%C3%A9rica_Central",
        "https://es.wikivoyage.org/wiki/Am%C3%A9rica_del_Sur",
        "https://es.wikivoyage.org/wiki/El_Caribe",
        "https://es.wikivoyage.org/wiki/M%C3%A9xico"]
    
    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,  # 1 segundo entre solicitudes
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "TurismoRAGBot/1.0 (proyecto academico; no comercial; ronald2mill4@gmail.com ) ",
        "DEPTH_LIMIT": 3,  # Limita la profundidad de rastreo 
        "CLOSESPIDER_PAGECOUNT": 1000, 
    }
    link_extractor = LinkExtractor(
        allow=r"es\.wikivoyage\.org/wiki/",
        deny=[r"/wiki/.*:", r"\?"],     # Descarta namespaces y queries
    )

    def parse(self, response):
        texto_limpio=clean_text(response.text)
        if is_relevant(response.url, texto_limpio):
            pais=contry_detection(response.url,texto_limpio)
            categoria=category_detection(texto_limpio)
            precio=price_detection(texto_limpio)
            item={
                "url":response.url,
                "titulo":response.css("h1::text").get().strip(),
                "texto": texto_limpio,
                "metadatos":{
                    "fuente": "wikivoyage",
                    "pais": pais,
                    "categoria": categoria,
                    "precio": precio,
                    "fecha": datetime.now().isoformat(),
                    "longitud": len(texto_limpio.split()),
                },
            }
            name=re.sub(r'[^\w]+', '_', response.url[-60:])+".json"
            contenido=json.dumps(item, ensure_ascii=False, indent=2)
            ok=r2_upload_file(name,contenido)
            estado="éxito" if ok else "error"
            self.logger.info(f"✓ [{categoria}] {item['titulo']} — {pais} ({estado})")
            yield item

        for link in self.link_extractor.extract_links(response):
            if is_relevant(link.url):
                yield response.follow(link.url, callback=self.parse)

if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(WikivoyageSpider)
    process.start()