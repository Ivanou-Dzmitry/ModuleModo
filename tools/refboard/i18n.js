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
    m: 'м', roof: 'КРОВЛЯ', texture: 'ТЕКСТУРА', materialN: n => `Материал ${n}`,
    modulesCount: (n, sizes) => `модулей: ${n} · ${sizes}`,
    noOverview: 'загрузите фото фасада', noModules: 'добавьте фото модулей', noPhoto: 'нет фото',
  },
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
  document.querySelectorAll('[data-lang]').forEach(b => b.classList.toggle('active', b.dataset.lang === uiLang));
}

function saveUiLang() {
  try { localStorage.setItem('refboard.lang', uiLang); } catch (e) { /* not critical */ }
}
