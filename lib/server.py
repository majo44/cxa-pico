from uasyncio import sleep, wait_for, start_server, TimeoutError
from config import web_port
from ir import RC5
from index_html import index_html
from rs import rs_send_power, rs_send_mute, rs_send_source

HTTP_STATUS = "HTTP/1.0 200 OK\r\n"
HTTP_CACHE = "Cache-Control: max-age=604800\r\n"
HTTP_CT_HTML = "Content-type: text/html\r\n"
HTTP_CT_CSS = "Content-type: text/css\r\n"
HTTP_CT_JSON = "Content-type: application/json\r\n"
HTTP_CT_JS = "Content-type: text/javascript\r\n"
HTTP_CT_PNG = "Content-type: image/png\r\n"
HTTP_HEADERS_END = "\r\n"

timeout = 3
ir = RC5()

def get_mime_header(file_name):
    if file_name.find('.js') > -1:
        return HTTP_CT_JS
    elif file_name.find('.png') > -1:
        return HTTP_CT_PNG
    elif file_name.find('.css') > -1:
        return HTTP_CT_CSS
    else:
        return "Content-type: application/octet-stream\r\n"

def read_file(file_name):
    with open('/lib'+ file_name, 'rb') as file:
        return file.read()


async def handle_file(file, writer):
    """
    Handling the request for file
    :param file: file path
    :param writer: output
    """
    file = file.split('?')[0]
    print("file:", file)
    try:
        writer.write(get_mime_header(file))
        writer.write(HTTP_CACHE)
        writer.write(HTTP_HEADERS_END)
        writer.write(read_file(file))
    except: 
        pass


async def handle_api(api, method, writer):
    """
    Handling the request for api:
    GET  /api/power - get the power state and respond with { ok: boolean, mute: boolean, source: string }
    POST /api/power - toggle the power and respond with { ok: boolean, mute: boolean, source: string }
    GET  /api/mute - get the mute state and respond with { ok: boolean } or { ok: false, "error": "amplifier turned off" }
    POST /api/mute - toggle the mute and respond with { ok: boolean } or { ok: false, "error": "amplifier turned off" }
    GET  /api/source - get the current source { ok: boolean, source: string } or { ok: false, "error": "amplifier turned off" }
    POST /api/source/x - set the source and respond with { ok: boolean } or { ok: false, "error": "amplifier turned off" }
    :param api: the api call
    :param method: the http method
    :param writer: output
    """
    print("api:", api)
    power = await wait_for(rs_send_power(), timeout)
    if api == 'power':
        if method == 'POST':
            await wait_for(rs_send_power(not power), timeout)            
            if not power:
                await sleep(1)
        power = await wait_for(rs_send_power(), timeout)
        mute = await wait_for(rs_send_mute(), timeout) if power else False
        source = await wait_for(rs_send_source(), timeout) if power else '-1'
        resp = f'{{ "ok": {"true" if power else "false"}, "mute": {"true" if mute else "false"}, "source": "{source}" }}'
    else:
        if power:
            if api == 'mute':
                mute = await wait_for(rs_send_mute(), timeout)
                if method == 'POST':
                    mute = await wait_for(rs_send_mute(not mute), timeout)
                resp = f'{{ "ok": {"true" if mute else "false"} }}'
            elif api.find('source') > -1:
                if method == 'POST':
                    source = api.split('/')[1]
                    current_source = await wait_for(rs_send_source(source), timeout)
                    resp = f'{{ "ok": {"true" if source == current_source else "false"}, "source": "{current_source}" }}'
                else:
                    current_source = await wait_for(rs_send_source(), timeout)
                    resp = f'{{ "ok": true, "source": "{current_source}" }}'
            elif api == 'vu':
                ir.v_up()
                resp = f'{{ "ok": true }}'
            elif api == 'vd':
                ir.v_down()
                resp = f'{{ "ok": true }}'
            else:
                resp = f'{{ "ok": false, "error": "unknown command" }}'
        else:
            resp = f'{{ "ok": false, "error": "amplifier turned off" }}'
    try:
        writer.write(HTTP_CT_JSON)
        writer.write(HTTP_HEADERS_END)
        writer.write(resp)
    except: 
        pass
    


async def handle_request(reader, writer):
    print("http client connected")

    request_line = await reader.readline()
    print("request:", request_line)

    r = str(request_line)
    m = r[2:(r.find("/") - 1)]
    r = r[r.find("/"):]
    r = r[0:r.find(" ")]

    print("method:", m)
    print("url:", r)

    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    try:
        writer.write(HTTP_STATUS)
        try:
            if r.find('/ping') == 0:
                writer.write('timeout')
            elif r.find('/public') == 0:
                await handle_file(r, writer)
            elif r.find('/api') == 0:
                await handle_api(r[5:], m, writer)
            else:
                power = await wait_for(rs_send_power(), timeout)
                mute = await wait_for(rs_send_mute(), timeout)
                source = await wait_for(rs_send_source(), timeout)
                writer.write(HTTP_CT_HTML)
                writer.write(HTTP_HEADERS_END)
                writer.write(index_html(power, mute, source))
        except TimeoutError:
            writer.write('timeout')

        await writer.drain()
        await writer.wait_closed()
        print("http client disconnected")
    except: 
        pass

def server_start(host="0.0.0.0", port=web_port):
    print("starting server", host, port)
    return start_server(handle_request, host, port)
