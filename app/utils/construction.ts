import type { GuideStep } from '~~/shared/types/project'

const stageLabels: Record<string, string> = {
  'Сначала разрешить привязку, не начинать стройку по старой метке': 'Проверить площадку',
  'Опоры, подиум и нижняя галерея': 'Опоры и подиум',
  'Только независимая добыча и новые вводы': 'Добыча и вводы',
  'НПЗ, кокс и безопасный пуск': 'НПЗ и утилизация',
  'F1 и техникаT0': 'F1 · Литьё и трубы',
  'F2 и техникаT1': 'F2 · Компоненты',
  'F3 и техника T2': 'F3 · Двигатели',
  'Экспорт и общий склад': 'Поезд и склад',
  'Оболочка, свет и маркировка': 'Фасад и свет',
  'Приёмка в игре': 'Проверить выпуск'
}

export function guideStageLabel(stage: GuideStep) {
  return stageLabels[stage.title] || constructionText(stage.title)
}

// Preserve immutable source data; repair only reviewed legacy prose at display time.
const proseCorrections: Record<string, string> = {
  'эквивалентныхпанелей': 'эквивалентных панелей',
  'натурнаядлинаобразцаобязательна': 'длину образца обязательно проверь в игре',
  'периметрподкрая': 'периметр по краям',
  'вычестьворота': 'вычесть ворота',
  'неприписыватьточныйметраждоотверстий': 'точный метраж уточни после разметки отверстий',
  'точныйметражпослемонтажа': 'точный метраж после монтажа',
  'ключевыхузла': 'ключевых узла',
  'локальныеманифольды': 'локальные манифольды',
  'накаждомразвороте': 'на каждом развороте',
  'науровень': 'на уровень',
  'плюснаружныеветви': 'плюс наружные ветви',
  'непо количествумашин': 'не по количеству машин',
  'сырьевыхвводов': 'сырьевых вводов',
  'наотправке': 'на отправке',
  'наприёме': 'на приёме',
  'железобетоннаябалка': 'железобетонная балка',
  'железобетонныхбалок': 'железобетонных балок',
  'переносныхбура': 'переносных бура',
  'тяжёлыхкаркасов': 'тяжёлых каркасов',
  'стальныхтруб': 'стальных труб',
  'модулястены': 'модуля стены',
  'принимающийсклад': 'принимающий склад',
  'каждойMkPlusмашины': 'каждой машины MkPlus',
  'один2мряд': 'один ряд высотой 2 м',
  '48слотовые': '48-слотовые',
  'сдачафаз': 'сдача фаз',
  'PureCaterium': 'Pure Caterium',
  'PureQuartz': 'Pure Quartz',
  'SmartPlating': 'Smart Plating'
}
const joinedProse = new RegExp(Object.keys(proseCorrections).join('|'), 'g')

const reviewedPhrases: [string, string][] = [
  ['T0 -88, полF1/НПЗ/депо -96.', 'Отметка пола T0: z = 88 м. Пол F1, нефтехимического двора и депо: z = 96 м.'],
  ['T1z108,F2z112.', 'Отметка пола T1: z = 108 м. Пол F2: z = 112 м.'],
  ['T2 z=124, F3 z=128.', 'Отметка пола T2: z = 124 м. Пол F3: z = 128 м.'],
  ['MkPlus Mk.3 capacity = base recipe ×10 at100%; no additional VU multiplier is credited to these mod classes.', 'Производительность MkPlus Mk.3 при частоте 100%: базовый рецепт ×10. Дополнительный множитель VU для этих модовых классов в расчёт не включён.'],
  ['HFO divides liquid ingredients/products by5; raw extractor supply is undivided. All fluid numbers are effective m³/min.', 'HFO делит объёмы жидких ингредиентов и продуктов на 5; объём добычи не делится. Все потоки жидкостей указаны в эффективных м³/мин.'],
  ['Unlocked Peak Efficiency Pipeline Mk.3 has stored flow limit20m³/s; design budgets only600m³/min, not nominal1200. Verify a325m³/min header before mass construction.', 'Peak Efficiency Pipeline Mk.3 открыт. В данных указан предел 20 м³/с, но проект закладывает только 600 м³/мин вместо номинальных 1200. До массовой постройки проверь один коллектор на 325 м³/мин.'],
  ['Existing100/min computer/frame plant and all saved extractor node IDs are protected. No existing supply or apparent unused productivity is credited to ME-100.', 'Действующий завод на 100 компьютеров и примерно 100 тяжёлых каркасов в минуту, а также все сохранённые ноды с экстракторами защищены. ME-100 не использует их снабжение или предполагаемую свободную производительность.'],
  ['New location is a ranked draft outside the protected plant envelope, not an approved construction address. Separate water pump placement, transport corridors, full geometry and terrain remain unverified.', 'Новая площадка — предварительный вариант вне защищённого контура завода, а не утверждённый адрес строительства. Отдельный водозабор, транспортные коридоры, полная геометрия и рельеф не проверены.'],
  ['Displayed footprints are reserved engineering cells based on shipped vanilla clearance and mod inheritance, not imported in-game mesh models.', 'Показаны зарезервированные инженерные клетки по штатным габаритам и наследованию модовых классов, а не импортированные игровые 3D-модели.'],
  ['WITHDRAWN: old location is not a construction recommendation. Existing100/min Computers and approximately100/min Heavy Modular Frames factory was not adequately included in the former ownership and clearance assessment.', 'Прежняя метка отозвана и не является рекомендацией для строительства. В прежней оценке владения и свободного места недостаточно учтён действующий завод на 100 компьютеров и примерно 100 тяжёлых модульных каркасов в минуту.'],
  ['Physical networks are undirected conservative reservations, not measured flows or a spare-capacity model.', 'Физические сети рассматриваются как ненаправленные защищённые контуры с запасом, а не как измеренные потоки или модель свободной мощности.'],
  ['Connected storage can join multiple production branches; these remain protected.', 'Подключённые склады могут объединять несколько производственных ветвей; все эти ветви остаются защищёнными.'],
  ['Only persistent saved factory/pipe connection components are traced; rail/truck/drone transfers and lightweight geometry require separate evidence.', 'Прослежены только сохранённые соединения заводского оборудования и труб. Железнодорожные, автомобильные и дроновые перевозки, а также облегчённая геометрия требуют отдельной проверки.'],
  ['Owner-reported industrial reservation remains authoritative even when a specific node has no direct extractor in this snapshot.', 'Заявленный владельцем промышленный резерв сохраняется, даже если у конкретной ноды нет прямого экстрактора в этом снимке.'],
  ['unlocked in current save; game geometry unverified', 'Открыто в текущем сохранении. Геометрия в игре не проверена.'],
  ['configured extractor expectation, not spare capacity or measured delivery', 'Расчёт по настройке экстрактора, не свободная мощность и не измеренная подача'],
  ['new dedicated oil extractor; zero existing output diverted', 'Отдельная новая нефтевышка; поток действующих производств не используется'],
  ['new dedicated extractor; zero existing output diverted', 'Отдельный новый экстрактор; поток действующих производств не используется'],
  ['exact rational equality for all 27 items', 'Точное равенство баланса для всех 27 изделий, рассчитанное рациональными числами'],
  ['match every recipe group', 'Количество размещений совпадает с каждой рецептурной группой'],
  ['six proposed solid/oil nodes have no existing extractor; separate water pump location remains unverified', 'На шести предложенных рудных и нефтяных нодах нет существующих экстракторов; место отдельного водозабора не проверено'],
  ['100 Computers/min and approximately100 Heavy Modular Frames/min protected; zero existing output allocated to ME-100', 'Завод на 100 компьютеров и примерно 100 тяжёлых модульных каркасов в минуту защищён; его выпуск не выделяется для ME-100'],
  ['candidate only; terrain, full geometry, separate water pump and corridors unverified', 'Только кандидат: рельеф, полная геометрия, отдельный водозабор и коридоры не проверены'],
  ['inside reserved clear floor heights', 'Габариты машин укладываются в зарезервированную чистую высоту этажей'],
  ['190 serialized SML session options in the current save header; persistent world-cost fields decoded independently. No persistent SML settings actor exists in this snapshot.', 'Из заголовка текущего сейва прочитаны 190 сохранённых параметров сессии SML. Постоянные поля стоимости мира разобраны независимо. Постоянного объекта настроек SML в этом снимке нет.'],
  ['Slow belt/lift/splitter downstream', 'Медленная лента, лифт или разветвитель дальше по маршруту'],
  ['Native entities, unlocks', 'Объекты игры и открытые рецепты'],
  ['contributing fingerprints', 'контрольные отпечатки участвующих источников'],
  ['unlocks', 'открытыми рецептами'],
  ['configured expectation, не spare capacity', 'расчёт по настройке, не свободная мощность'],
  ['Все downloads', 'Все файлы для скачивания'],
  ['raw save binary', 'исходный бинарный сейв'],
  ['При этих unknowns', 'При этих неопределённостях'],
  ['lightweight-геометрия', 'облегчённая геометрия'],
  ['Фасад: module', 'Фасад: модуль'],
  ['Фасад: quantities', 'Фасад: количества'],
  ['Фасад: openings', 'Фасад: проёмы'],
  ['Фасад: structure', 'Фасад: опоры'],
  ['Фасад: stairs', 'Фасад: лестницы'],
  ['Фасад: roof', 'Фасад: крыша'],
  ['build-manifest / visuals provenance', 'Манифест сборки и происхождение иллюстраций'],
  ['atlas.js projection constants', 'Константы проекции atlas.js'],
  ['unverified; saves/configs untouched in this milestone', 'Не проверено; сейвы и конфигурация на этом этапе не менялись'],
  ['material_conservation', 'Баланс материалов'],
  ['target_per_min', 'Целевой выпуск в минуту'],
  ['manufacturing_machines', 'Производственные машины'],
  ['manufacturing_clock_max', 'Максимальная доля частоты машин'],
  ['placement_counts', 'Количество размещений'],
  ['service_cell_overlaps', 'Пересечения сервисных клеток'],
  ['oil_headers', 'Нефтяные коллекторы'],
  ['oil_header_capacity', 'Ёмкость нефтяного коллектора'],
  ['rubber_export_lanes', 'Линии вывоза резины'],
  ['rubber_bank_crossfeed', 'Переток между банками резины'],
  ['coke_sink_rates', 'Потоки кокса в утилизаторы'],
  ['coke_sink_lines', 'Линии утилизации кокса'],
  ['raw_extraction', 'Независимая добыча'],
  ['existing_factory', 'Действующий завод'],
  ['construction_ready: False', 'Готовность к строительству: нет'],
  ['site_approval', 'Согласование площадки'],
  ['machine_ceiling_envelopes', 'Высотные габариты машин'],
  ['game_runtime: unverified', 'Работа в игре: не проверена'],
  ['terrain_collision: unverified', 'Коллизии с рельефом: не проверены']
]

export function constructionText(text: string) {
  for (const [source, replacement] of reviewedPhrases) text = text.replaceAll(source, replacement)
  return text
    .replace(joinedProse, phrase => proseCorrections[phrase]!)
    .replaceAll('MkPlusMk.3', 'MkPlus Mk.3')
    .replaceAll('PipelineMk.3', 'Pipeline Mk.3')
    .replaceAll('пог.м', 'пог. м')
    .replace('Площадка не утверждена: REJECTED_PENDING_REPLAN; construction_ready=false.', 'Площадка ещё не утверждена. Старую метку не используй для строительства.')
    .replace(/construction_ready=false\.?/g, 'площадка пока не готова к строительству.')
    .replace(/([А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])/g, '$1 ')
    .replace(/([а-яё])(?=[A-Z])/g, '$1 ')
    .replace(/(\d)(?=ME|Motor|Rubber|Plastic|Coke|Pure|Smart|RIP|AI|HFO|SINK)/g, '$1 ')
    .replace(/([,;:])(?=[А-Яа-яЁёA-Za-z])/g, '$1 ')
    .replace(/([А-Яа-яЁёA-Za-z]),(?=\d)/g, '$1, ')
    .replace(/([;:])(?=\d)/g, '$1 ')
    .replace(/([+−])(?=[А-Яа-яЁё])/g, '$1 ')
    .replace(/(?<=\d)(?=Mk\.)/g, ' ')
    .replace(/([А-Яа-яЁё])(?=Mk\.)/g, '$1 ')
    .replace(/\s{2,}/g, ' ')
    .trim()
}
