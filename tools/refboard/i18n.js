'use strict';

// Interface strings. A value is a string or a function of its arguments.
const UI_TEXT = {
  ru: {
    brandSub: 'фасад и модули → лист 1980×1020',
    openProject: 'Открыть проект', saveProject: 'Сохранить проект', exportPng: 'Скачать PNG',
    s1: '1. Проект', s2: '2. Сетка и этажи', s3: '3. Общий вид', s4: '4. Модули', s5: '5. Схема фасада', s6: '6. Материалы',
    moduleDrop: 'Перетащите фото модулей сюда или нажмите, чтобы выбрать',
    cropHint: 'В рамке: тяните мышью — сдвиг, колесо — масштаб, двойной клик — сброс.',
    layoutHint: 'Выберите модуль и кликайте по клеткам. Правый клик — очистить клетку.',

    title: 'Название дома', subtitle: 'Подзаголовок', note: 'Описание', author: 'Автор', date: 'Дата',
    accent: 'Акцентный цвет', bg: 'Цвет фона листа', ink: 'Цвет текста и линий',
    defaults: 'Цвета по умолчанию', reset: 'Сбросить', sheetLang: 'Язык листа',

    grid: 'Шаг сетки, м', bays: 'Пролётов по ширине', groundH: 'Высота 1-го этажа, м',
    upperH: 'Высота верхних этажей, м', upperFloors: 'Верхних этажей', roof: 'Крыша на схеме',

    ovReplace: 'Заменить фото фасада', ovDrop: 'Перетащите фото фасада сюда или нажмите',
    ovHint: 'Кадр общего вида на листе.', remove: 'Удалить',

    sizeOpt: (w, h) => `${w} × ${h} м`, customSize: 'свой размер',
    code: 'Код', size: 'Размер (Ш × В)', name: 'Название', caption: 'Подпись', width: 'Ширина, м', height: 'Высота, м',

    addModulesFirst: 'Сначала добавьте модули.', eraser: 'Ластик', none: '— нет —',
    cellTitle: (f, b) => `этаж ${f}, пролёт ${b}`,
    filler: 'Заполнитель (пустые клетки и место под низким модулем)', clearLayout: 'Очистить схему',

    material: 'Материал', otherPhoto: 'Другое фото', photo: 'Фото', colour: 'Цвет',
    matDrop: 'Перетащите сюда фото материала (кирпич, штукатурка, черепица…)',
    takeColours: 'Взять цвета с фото', addColour: '+ цвет', addMaterial: '+ материал (фото)',
    matHint: 'До 6 материалов: цвет или фото текстуры. Фото обрезается квадратом — тяните мышью, колесо — масштаб.',
    loadError: 'Не удалось открыть проект: ',
    help: 'Помощь', close: 'Закрыть',
    swatchSize: 'Сторона квадрата на листе, px (0 или пусто — авто)', auto: 'авто',
    depthBays: 'Пролётов по глубине (сбоку), 0 — без бокового', front: 'Главный фасад', side: 'Боковой фасад',
    viewSheet: 'Лист', view3d: '3D-вид', roofColour: 'Цвет крыши', resetView: 'Сбросить вид',
    snapshot: 'Снимок в «Общий вид»', export3d: 'Скачать PNG 3D',
    hint3d: 'Тяните мышью — вращение, колесо — приближение. Спереди главный фасад, по бокам боковой, сзади стена-заполнитель.',
    noWebgl: 'Браузер не поддерживает WebGL2, 3D-вид недоступен.',
  },
  en: {
    brandSub: 'facade and modules → 1980×1020 sheet',
    openProject: 'Open project', saveProject: 'Save project', exportPng: 'Download PNG',
    s1: '1. Project', s2: '2. Grid and floors', s3: '3. General view', s4: '4. Modules', s5: '5. Facade layout', s6: '6. Materials',
    moduleDrop: 'Drop module photos here or click to choose',
    cropHint: 'In the frame: drag to move, wheel to zoom, double-click to reset.',
    layoutHint: 'Pick a module and click the cells. Right-click clears a cell.',

    title: 'Building name', subtitle: 'Subtitle', note: 'Description', author: 'Author', date: 'Date',
    accent: 'Accent colour', bg: 'Sheet background', ink: 'Text and line colour',
    defaults: 'Default colours', reset: 'Reset', sheetLang: 'Sheet language',

    grid: 'Grid step, m', bays: 'Bays across', groundH: 'Ground floor height, m',
    upperH: 'Upper floor height, m', upperFloors: 'Upper floors', roof: 'Roof on the layout',

    ovReplace: 'Replace the facade photo', ovDrop: 'Drop a facade photo here or click',
    ovHint: 'Frame of the general view on the sheet.', remove: 'Remove',

    sizeOpt: (w, h) => `${w} × ${h} m`, customSize: 'custom size',
    code: 'Code', size: 'Size (W × H)', name: 'Name', caption: 'Caption', width: 'Width, m', height: 'Height, m',

    addModulesFirst: 'Add modules first.', eraser: 'Eraser', none: '— none —',
    cellTitle: (f, b) => `floor ${f}, bay ${b}`,
    filler: 'Filler (empty cells and the gap under a low module)', clearLayout: 'Clear layout',

    material: 'Material', otherPhoto: 'Another photo', photo: 'Photo', colour: 'Colour',
    matDrop: 'Drop a material photo here (brick, plaster, roof tiles…)',
    takeColours: 'Take colours from photos', addColour: '+ colour', addMaterial: '+ material (photo)',
    matHint: 'Up to 6 materials: a colour or a texture photo. The photo is cut to a square: drag to move, wheel to zoom.',
    loadError: 'Could not open the project: ',
    help: 'Help', close: 'Close',
    swatchSize: 'Swatch side on the sheet, px (0 or empty = auto)', auto: 'auto',
    depthBays: 'Bays in depth (side), 0 = no side', front: 'Front', side: 'Side',
    viewSheet: 'Sheet', view3d: '3D view', roofColour: 'Roof colour', resetView: 'Reset view',
    snapshot: 'Snapshot to "General view"', export3d: 'Download 3D PNG',
    hint3d: 'Drag to orbit, wheel to zoom. Front elevation at the front, side elevation on both sides, filler wall at the back.',
    noWebgl: 'This browser has no WebGL2, so the 3D view is not available.',
  },
};

// Text drawn on the sheet itself; follows the project's sheet language, not the interface.
const SHEET_TEXT = {
  en: {
    general: 'General view', layout: 'Module layout', modules: 'Modules', materials: 'Materials',
    photoRef: 'Street elevation · photo reference',
    grid: 'GRID', floors: 'FLOORS', author: 'AUTHOR', date: 'DATE',
    gridValue: g => `${g} m module`,
    floorsValue: (ground, upper, count) => count === 0 ? `GF ${ground} m`
      : count === 1 ? `GF ${ground} m · 1F ${upper} m` : `GF ${ground} m · 1–${count}F ${upper} m`,
    front: 'FRONT ELEVATION', side: 'SIDE ELEVATION',
    m: 'm', roof: 'ROOF', texture: 'TEXTURE', materialN: n => `Material ${n}`,
    modulesCount: (n, sizes) => `${n} modules · ${sizes}`,
    noOverview: 'upload a facade photo', noModules: 'add module photos', noPhoto: 'no photo',
  },
  ru: {
    general: 'Общий вид', layout: 'Схема модулей', modules: 'Модули', materials: 'Материалы',
    photoRef: 'Уличный фасад · фото-референс',
    grid: 'СЕТКА', floors: 'ЭТАЖИ', author: 'АВТОР', date: 'ДАТА',
    gridValue: g => `модуль ${g} м`,
    floorsValue: (ground, upper, count) => count === 0 ? `1 эт. ${ground} м`
      : count === 1 ? `1 эт. ${ground} м · 2 эт. ${upper} м` : `1 эт. ${ground} м · 2–${count + 1} эт. ${upper} м`,
    front: 'ГЛАВНЫЙ ФАСАД', side: 'БОКОВОЙ ФАСАД',
    m: 'м', roof: 'КРОВЛЯ', texture: 'ТЕКСТУРА', materialN: n => `Материал ${n}`,
    modulesCount: (n, sizes) => `модулей: ${n} · ${sizes}`,
    noOverview: 'загрузите фото фасада', noModules: 'добавьте фото модулей', noPhoto: 'нет фото',
  },
};

// Help dialog content (trusted static HTML).
const HELP_HTML = {
  ru: `
    <h2>Как собрать рефборд</h2>
    <ol>
      <li><b>Проект.</b> Название дома, автор, дата. Здесь же цвета листа (акцент, фон, текст) и язык листа.</li>
      <li><b>Сетка и этажи.</b> Шаг сетки (обычно 3 м), сколько пролётов по ширине, высота 1-го этажа (4 м)
        и верхних (3 м), сколько верхних этажей.</li>
      <li><b>Общий вид.</b> Перетащите фото всего фасада и выберите кадр.</li>
      <li><b>Модули.</b> Перетащите фото окон, дверей, балкона, стены. Каждому задайте код (<code>W-01</code>,
        <code>D-01</code>, <code>BR-01</code>), название, подпись и размер: 3 × 3 м, 3 × 4 м или свой.</li>
      <li><b>Схема фасада.</b> Выберите модуль кнопкой и кликайте по клеткам. Правый клик очищает клетку.
        Заполнитель (обычно кирпичная стена) закрывает пустые клетки и место под низким модулем.
        Кнопки «Главный / Боковой» переключают фасад; глубина дома задаётся в «Сетке». Глухая боковая
        стена получается сама — просто оставьте клетки пустыми.</li>
      <li><b>Материалы.</b> До 6 образцов: «Взять цвета с фото» или фото текстуры (кирпич, штукатурка,
        черепица) — оно обрежется квадратом. Размер квадратов подбирается сам или задаётся вручную.</li>
      <li><b>Скачать PNG</b> — готовый лист 1980×1020. <b>Сохранить проект</b> — файл <code>.json</code>
        с фото внутри, его можно открыть позже.</li>
    </ol>
    <h3>3D-вид</h3>
    <p>Кнопка «3D-вид» над листом показывает дом коробкой из ваших модулей: спереди главный фасад, по бокам
      боковой, сзади стена-заполнитель. Тяните мышью — вращение, колесо — приближение. «Снимок в „Общий вид“»
      кладёт текущий ракурс в раздел 01 листа. «Скачать PNG 3D» сохраняет кадр 1980×1020 с шапкой листа.</p>
    <h3>Кадрирование в рамке</h3>
    <p>Тяните мышью — сдвиг, колесо — масштаб, двойной клик — сброс.</p>
    <h3>Советы</h3>
    <ul>
      <li>Выровняйте перспективу фото заранее (Photoshop: Perspective Crop, GIMP: Perspective).</li>
      <li>Одинаковые окна — один модуль. Обычно на дом хватает 5–8 модулей.</li>
      <li>Фото никуда не отправляются: всё работает в вашем браузере.</li>
    </ul>`,
  en: `
    <h2>How to build a reference board</h2>
    <ol>
      <li><b>Project.</b> Building name, author, date. Sheet colours (accent, background, text) and sheet language
        are here too.</li>
      <li><b>Grid and floors.</b> Grid step (usually 3 m), number of bays, ground floor height (4 m),
        upper floor height (3 m), number of upper floors.</li>
      <li><b>General view.</b> Drop a photo of the whole facade and choose the frame.</li>
      <li><b>Modules.</b> Drop photos of windows, doors, a balcony, a wall. Give each one a code (<code>W-01</code>,
        <code>D-01</code>, <code>BR-01</code>), a name, a caption and a size: 3 × 3 m, 3 × 4 m or custom.</li>
      <li><b>Facade layout.</b> Pick a module with its button and click the cells. Right-click clears a cell.
        The filler (usually the brick wall) covers empty cells and the gap under a low module.
        The Front / Side buttons switch the elevation; the house depth is set in "Grid". A blank side wall
        needs nothing: leave its cells empty.</li>
      <li><b>Materials.</b> Up to 6 swatches: "Take colours from photos" or a texture photo (brick, plaster,
        roof tiles), cut to a square. The swatch size is automatic or set by hand.</li>
      <li><b>Download PNG</b> gives the 1980×1020 sheet. <b>Save project</b> gives a <code>.json</code> file
        with the photos inside, to open later.</li>
    </ol>
    <h3>3D view</h3>
    <p>The "3D view" button above the sheet shows the house as a box made of your modules: the front elevation
      at the front, the side elevation on both sides, the filler wall at the back. Drag to orbit, wheel to zoom.
      "Snapshot to General view" puts the current angle into section 01 of the sheet. "Download 3D PNG" saves a
      1980×1020 frame with the sheet header.</p>
    <h3>Framing a photo</h3>
    <p>Drag to move, mouse wheel to zoom, double-click to reset.</p>
    <h3>Tips</h3>
    <ul>
      <li>Straighten the photo perspective first (Photoshop: Perspective Crop, GIMP: Perspective).</li>
      <li>Identical windows are one module. A house usually needs 5–8 modules.</li>
      <li>Photos never leave your computer: everything runs in your browser.</li>
    </ul>`,
};

const LANGS = ['ru', 'en'];

function lookup(table, lang, key, args) {
  const v = table[lang]?.[key] ?? table.en[key] ?? key;
  return typeof v === 'function' ? v(...args) : v;
}

function initialUiLang() {
  try {
    const saved = localStorage.getItem('refboard.lang');
    if (LANGS.includes(saved)) return saved;
  } catch (e) { /* storage blocked: fall back to the browser language */ }
  return (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

let uiLang = initialUiLang();

const t = (key, ...args) => lookup(UI_TEXT, uiLang, key, args);

// Every element with data-i18n gets its text from the interface table.
function applyStaticText() {
  document.documentElement.lang = uiLang;
  document.querySelectorAll('[data-i18n]').forEach(e => { e.textContent = t(e.dataset.i18n); });
  document.querySelectorAll('[data-i18n-title]').forEach(e => { e.title = t(e.dataset.i18nTitle); });
  const help = document.getElementById('helpBody');
  if (help) help.innerHTML = HELP_HTML[uiLang] || HELP_HTML.en;
  document.querySelectorAll('[data-lang]').forEach(b => b.classList.toggle('active', b.dataset.lang === uiLang));
}

function saveUiLang() {
  try { localStorage.setItem('refboard.lang', uiLang); } catch (e) { /* not critical */ }
}
