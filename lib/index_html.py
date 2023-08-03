head = f"""
<head>
    <link rel="apple-touch-icon" sizes="180x180" href="/public/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/public/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/public/favicon-16x16.png">
    <link rel="manifest" href="/public/site.webmanifest">
    <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Rubik">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <title>CXA pico</title>
    <script src="/public/script.js"></script>
    <link rel="stylesheet" href="/public/styles.css">
</head>
"""


def source_btn(code, current_source, power, ctn):
    return f"""
        <button class="{'on' if current_source == code else ''}" 
            data-command="source" 
            data-command-arg="{code}" 
            {'disabled' if not power else ''}>
            {ctn}
        </button>
    """


def index_html(power, mute, current_source):
    btn_disabled = 'disabled' if not power else ''
    return f"""<!DOCTYPE html>
<html lang="pl">
    {head}
    <body>
        <div class="indicator"></div>
        <header>
            <button class="{'on' if power else ''}" data-command="power">
                <span>power_settings_new</span>
            </button>
            <div class="logo">
                <span>CXA</span>
                <span>pico</span>
            </div>
            <button class="{'on' if mute else ''}" data-command="mute" {btn_disabled}>
                <span>volume_off</span>
            </button>
        </header>
    
        <main>
            <section class="volume">
                <button data-command-type="long" data-command="vd" {btn_disabled}>
                    <span>volume_down</span>
                </button>
                <button data-command-type="long" data-command="vu" {btn_disabled}>
                    <span>volume_up</span>
                </button>
            </section>
            <section class="source">
                <div class="label">Source</div>
                <div class="grid">
                    {source_btn('00', current_source, power, 'A1')}
                    {source_btn('01', current_source, power, 'A2')}
                    {source_btn('02', current_source, power, 'A3')}
                    {source_btn('03', current_source, power, 'A4')}
                    {source_btn('04', current_source, power, 'D1')}
                    {source_btn('05', current_source, power, 'D2')}
                    {source_btn('06', current_source, power, 'D3')}
                    {source_btn('22', current_source, power, 'D4')}
                    {source_btn('10', current_source, power, '<span>settings_input_hdmi</span>')}
                    {source_btn('14', current_source, power, '<span>bluetooth</span>')}
                    {source_btn('16', current_source, power, '<span>usb</span>')}
                    {source_btn('10', current_source, power, 'A1 <sub>balanced</sub>')}
                </div>
            </section>
        </main>
        <footer>
            with love to <span class="rp"></span> by majo44
        </footer>
    </body>
</html>
    """
