"""
Simple utilities for Perfecto MCP tools.
"""
import platform
from datetime import datetime
from typing import Optional, Callable
from urllib.parse import urljoin

import httpx
import lxml.html

from config.token import PerfectoToken
from config.version import __version__
from models.result import BaseResult

so = platform.system()  # "Windows", "Linux", "Darwin"
version = platform.version()  # kernel / build version
release = platform.release()  # ex. "10", "5.15.0-76-generic"
machine = platform.machine()  # ex. "x86_64", "AMD64", "arm64"

ua_part = f"{so} {release}; {machine}"
user_agent = f"perfecto-mcp/{__version__} ({ua_part})"
timeout = httpx.Timeout(
    connect=15.0,
    read=60.0,
    write=15.0,
    pool=60.0
)


async def api_request(token: Optional[PerfectoToken], method: str, endpoint: str,
                      result_formatter: Callable = None,
                      result_formatter_params: Optional[dict] = None,
                      **kwargs) -> BaseResult:
    """
    Make an authenticated request to the Perfecto API.
    Handles authentication errors gracefully.
    """
    if not token:
        return BaseResult(
            error="No API token. Set PERFECTO_SECURITY_TOKEN or PERFECTO_SECURITY_TOKEN_FILE env var with security token."
        )

    headers = kwargs.pop("headers", {})
    headers["Perfecto-Authorization"] = token.token
    headers["User-Agent"] = user_agent

    async with (httpx.AsyncClient(base_url="", http2=True, timeout=timeout) as client):
        try:
            resp = await client.request(method, endpoint, headers=headers, **kwargs)
            resp.raise_for_status()
            result = resp.json()
            error = None
            if isinstance(result, list) and len(result) > 0 and "userMessage" in result[0]:  # It's an error
                final_result = None
                error = result[0].get("userMessage", None)
            else:
                final_result = result_formatter(result, result_formatter_params) if result_formatter else result
            return BaseResult(
                result=final_result,
                error=error,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                return BaseResult(
                    error="Invalid credentials"
                )
            raise


async def http_request(method: str, endpoint: str,
                       result_formatter: Callable = None,
                       result_formatter_params: Optional[dict] = None,
                       **kwargs) -> BaseResult:
    """
    Make an http request to the Perfecto Webpage.
    """

    headers = kwargs.pop("headers", {})
    headers["User-Agent"] = user_agent

    async with (httpx.AsyncClient(base_url="", http2=True, timeout=timeout) as client):
        try:
            resp = await client.request(method, endpoint, headers=headers, **kwargs)
            resp.raise_for_status()
            result = resp.text
            error = None
            final_result = result_formatter(result, result_formatter_params) if result_formatter else result
            return BaseResult(
                result=final_result,
                error=error,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [401, 403]:
                return BaseResult(
                    error="Invalid credentials"
                )
            raise


def get_date_time_iso(timestamp: int) -> Optional[str]:
    if timestamp is None:
        return None
    else:
        return datetime.fromtimestamp(timestamp).isoformat()


def clean_text(text, preserve_newlines=False):
    """Limpia el texto removiendo NBSP y normalizando espacios"""
    text = text.replace('\xa0', ' ')

    if preserve_newlines:
        lines = text.split('\n')
        cleaned_lines = [' '.join(line.split()) for line in lines]
        return '\n'.join(cleaned_lines).strip()
    else:
        text = ' '.join(text.split())
        return text.strip()


def extract_text_with_br(element):
    """Extrae texto de un elemento convirtiendo <br> en saltos de línea"""
    html_str = lxml.html.tostring(element, encoding='unicode', method='html')
    # Reemplazar <br> con saltos de línea
    html_str = html_str.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    # Crear nuevo elemento y extraer texto
    temp = lxml.html.fromstring(html_str)
    return temp.text_content()


def table_to_markdown(table, base_url=None):
    """Convierte una tabla HTML a formato Markdown"""
    rows = table.xpath('.//tr')
    if not rows:
        return ""

    markdown = []

    # Extraer headers
    header_row = table.xpath('.//thead//tr[1] | .//tr[1]')
    if header_row:
        headers = []
        for th in header_row[0].xpath('.//th | .//td'):
            # Procesar elementos inline en headers (incluyendo links)
            header_text = process_inline_elements(th, base_url)
            header_text = clean_text(header_text)
            headers.append(header_text)

        if headers and any(h for h in headers if h):
            markdown.append("| " + " | ".join(headers) + " |")
            markdown.append("| " + " | ".join(["---"] * len(headers)) + " |")
            start_idx = 1
        else:
            start_idx = 0
    else:
        start_idx = 0

    # Extraer filas de datos
    for row in rows[start_idx:]:
        cells = row.xpath('.//td | .//th')
        if cells:
            cell_texts = []
            for cell in cells:
                # Procesar elementos inline en celdas (incluyendo links)
                cell_text = process_inline_elements(cell, base_url)
                cell_text = clean_text(cell_text)
                cell_texts.append(cell_text)

            if any(cell_texts):
                markdown.append("| " + " | ".join(cell_texts) + " |")

    return "\n".join(markdown) if markdown else ""


def process_inline_elements(element, base_url=None, debug=False):
    """Procesa elementos inline como links, negrita, etc."""
    parts = []

    if element.text:
        parts.append(element.text)

    for child in element:
        tag = child.tag.lower()

        if tag == 'a':
            href = child.get('href', '')
            text = child.text_content().strip()

            # Convertir links relativos a absolutos
            if href and base_url:
                href = urljoin(base_url, href)

            if debug:
                print(f"  Link encontrado: texto='{text}', href='{href}'")

            # Filtrar links de "Copy" y javascript:void
            if text.lower() in ['copy', 'link', ''] or 'javascript:' in href:
                if child.tail:
                    parts.append(child.tail)
                continue

            if text and href:
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)
        elif tag == 'br':
            parts.append('\n')
        elif tag in ['strong', 'b']:
            text = child.text_content().strip()
            if text:
                parts.append(f"**{text}**")
        elif tag in ['em', 'i']:
            text = child.text_content().strip()
            if text:
                parts.append(f"*{text}*")
        elif tag == 'code':
            text = child.text_content().strip()
            if text:
                parts.append(f"`{text}`")
        else:
            # Procesar recursivamente para manejar links anidados
            inner_result = process_inline_elements(child, base_url)
            if inner_result:
                parts.append(inner_result)

        if child.tail:
            parts.append(child.tail)

    return ''.join(parts)


def element_to_markdown(element, base_url=None, level=0):
    """Convierte un elemento HTML a Markdown recursivamente"""
    tag = element.tag.lower()
    result = []

    # Headers
    if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level_num = int(tag[1])
        text = clean_text(element.text_content())
        if text:
            result.append(f"{'#' * level_num} {text}\n")

    # Párrafos con soporte para elementos inline
    elif tag == 'p':
        text = process_inline_elements(element, base_url)
        text = clean_text(text)
        if text:
            result.append(f"{text}\n")

    # Listas con soporte para links inline
    elif tag == 'ul':
        for li in element.xpath('./li'):
            text = process_inline_elements(li, base_url)
            text = clean_text(text)
            if text:
                result.append(f"- {text}\n")
        result.append("")

    elif tag == 'ol':
        for i, li in enumerate(element.xpath('./li'), 1):
            text = process_inline_elements(li, base_url)
            text = clean_text(text)
            if text:
                result.append(f"{i}. {text}\n")
        result.append("")

    # Tablas
    elif tag == 'table':
        table_md = table_to_markdown(element, base_url)
        if table_md:
            result.append(f"{table_md}\n")

    # Código con detección de lenguaje y filtrado de "Copy"
    elif tag == 'pre' or 'codesnippet' in element.get('class', '').lower():
        # Buscar el lenguaje antes del código
        lang = ""
        code_element = element

        # Buscar elementos de lenguaje comunes
        lang_elem = element.xpath('.//*[contains(@class, "language")]')
        if not lang_elem:
            # Buscar por texto que indique el lenguaje (JavaScript, Java, Python, etc.)
            for child in element:
                child_text = child.text_content().strip().lower()
                if child_text in ['javascript', 'java', 'python', 'ruby', 'go', 'php', 'c#', 'csharp', 'typescript',
                                  'bash', 'shell', 'sql', 'json', 'xml', 'yaml', 'css', 'html']:
                    lang = child_text
                    break

        # Si hay un elemento code dentro de pre, usar ese
        code_children = element.xpath('.//code')
        if code_children:
            code_element = code_children[0]
            class_attr = code_element.get('class', '')
            if 'language-' in class_attr:
                lang = class_attr.split('language-')[1].split()[0]

        # Extraer el código
        code_text = extract_text_with_br(code_element)
        code_text = clean_text(code_text, preserve_newlines=True)

        # Filtrar "Copy" al inicio
        lines = code_text.split('\n')
        filtered_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            line_stripped = line.strip().lower()
            # Saltar líneas que solo dicen "copy" o lenguajes conocidos
            if line_stripped in ['copy', 'javascript', 'java', 'python', 'ruby', 'go', 'php', 'c#', 'csharp',
                                 'typescript', 'bash', 'shell', 'sql', 'json', 'xml', 'yaml', 'css', 'html']:
                if line_stripped != 'copy':
                    lang = line_stripped
                continue
            filtered_lines.append(line)

        code_text = '\n'.join(filtered_lines).strip()

        if code_text:
            result.append(f"```{lang}\n{code_text}\n```\n")

    # Blockquotes
    elif tag == 'blockquote':
        text = extract_text_with_br(element)
        text = clean_text(text)
        if text:
            for line in text.split('\n'):
                if line.strip():
                    result.append(f"> {line}\n")
            result.append("")

    # HR
    elif tag == 'hr':
        result.append("---\n")

    # Imágenes con URLs absolutas
    elif tag == 'img':
        alt = element.get('alt', '')
        src = element.get('src', '')
        if src:
            # Convertir src relativo a absoluto
            if base_url:
                src = urljoin(base_url, src)
            result.append(f"![{alt}]({src})\n")

    # Elementos a ignorar
    elif tag in ['script', 'style', 'noscript', 'meta', 'link', 'head']:
        pass

    # Para cualquier otro elemento, procesar sus hijos
    else:
        for child in element:
            child_md = element_to_markdown(child, base_url, level + 1)
            if child_md:
                result.extend(child_md)

    return result


def html_to_markdown(html_content, base_url=None):
    """Convierte HTML a Markdown"""
    tree = lxml.html.fromstring(html_content)

    # Buscar el div con role="main"
    main_div = tree.xpath('//div[@role="main"]')
    if not main_div:
        main_div = tree.xpath('//main | //div[@class="main"] | //article | //body')

    if not main_div:
        return "# Error\n\nNo se encontró el contenedor principal"

    main_div = main_div[0]

    # Procesar todos los elementos
    markdown_lines = []
    for child in main_div:
        result = element_to_markdown(child, base_url)
        if result:
            markdown_lines.extend(result)

    # Unir todo
    markdown = "".join(markdown_lines)

    # Limpiar múltiples líneas en blanco
    while "\n\n\n" in markdown:
        markdown = markdown.replace("\n\n\n", "\n\n")

    return markdown.strip()
