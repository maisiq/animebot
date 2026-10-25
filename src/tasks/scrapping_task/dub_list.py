"""Словарь известных студий озвучки.

Используется season-скраппером, чтобы отличать значения блока «Озвучка» на
странице аниме от смежных блоков сетки («Тип», «Студия», «Выход» и т.п.):
значение считается озвучкой, если оно присутствует здесь (или в таблице
voiceover_studios) либо является ссылкой вида /anime/voiceover/...

Можно пополнять вручную и через админ-команду /add_studio.
"""

DUB_LIST = [
    'AniLibria',
    'AniLibria TV',
    'AniDUB',
    'AniRise',
    'AnimeVost',
    'JAM CLUB',
    'SHIZA Project',
    'ShowTrezv',
    'Dream Cast',
    'UndeadStudio',
    'NoviFanime',
    'FumoFlow',
    'Kansou Team',
    'On viewpoint',
    'MIXLINE Production',
    'SoDBTeam',
    'AnimAbility',
    'Subtitry',
    'MyAmigos',
    'AstralEpisode',
    'Double Stream',
    'Re-Dream',
    'Yu-Nova',
    'CoreToNet',
    'Crist Mini',
    'Экзвук',
    'Студийная Банда',
    'Субтитры',
    'Wakanim',
    'Shizon',
    'AniMedia',
    'AniMaunt',
    'AniOxygen',
    'Mahou Studio',
    'Kisaka',
    'Inufilth',
    'GhostDub',
    'Yumeko',
    'AniStar',
    'Milkyway',
    'Takri',
    'SilverRecord',
    'TataruFanSubs',
]
