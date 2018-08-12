import asyncio, arpeggio, discord, hjson, os, pprint, re, sys
from ithkuil.morphology.words import Factory
from ithkuil.morphology.exceptions import AnalysisException

SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

with open('lexicon.hjson') as f: lexicon = hjson.load(f)
with open('suffixes.hjson') as f: suffixes = hjson.load(f)
with open('biases.hjson') as f: biases = hjson.load(f)

def normalize(s):
    s = s.replace('\N{left single quotation mark}', "'")
    s = s.replace('\N{right single quotation mark}', "'")
    s = s.replace('\N{left double quotation mark}', '"')
    s = s.replace('\N{right double quotation mark}', '"')
    s = s.replace('\N{modifier letter acute accent}', '\N{acute accent}')
    s = s.replace('\N{modifier letter grave accent}', '\N{grave accent}')
    s = s.replace('\N{modifier letter small h}', 'h')
    s = re.sub('ẍ|ẋ|x̌', 'xh', s)
    s = re.sub('ḑ|đ|ḏ', 'dh', s)
    s = re.sub('ı', 'i', s)
    return s

def fix_parens(s):
    return s.replace(') (', ', ')

def lexicon_lookup(root, designation, stem_and_pattern):
    d = 0 if designation == 'IFL' else 1
    p = int(stem_and_pattern[1]) - 1
    s = int(stem_and_pattern[3]) - 1
    return lexicon_lookup_(root, d, p, s)

def lexicon_lookup_(root, d, p, s):
    print('lexicon_lookup_', root, d, p, s)
    dps = ''
    if (d, p, s) != (0, 0, 0):
        dps = ('-%s-P%dS%d' % (['IFL', 'FML'][d], p + 1, s + 1)).translate(SUB)

    root = normalize(root)
    if root not in lexicon:
        return "%s%s" % (root, dps)
    entry = lexicon[root]
    if isinstance(entry, str):
        return "%s%s" % (entry, dps)

    if isinstance(entry[0], str):
        command = entry[0]
        if command.startswith('@'):
            # Template
            res = lexicon_lookup_(command, d, p, s)
            if command == '@kh' and '/' in entry[1]:
                res = res.replace('@ relation (dominant)', entry[1].split('/')[0].strip())
                res = res.replace('@ relation (passive)', entry[1].split('/')[1].strip())
            elif len(entry) > 2:
                for i in range(1, len(entry)):
                    res = res.replace('@' + str(i), entry[i])
                return res
            return res.replace('@', entry[1])
        elif command.startswith('+'):
            # Addendum
            res = lexicon_lookup_(command[1:], d, p, s)
            res = fix_parens(res + ' (' + entry[1] + ')')
            return res
        else:
            raise ValueError('Invalid command: ' + command)

    x = entry[d]
    if isinstance(x, str):
        res = lexicon_lookup_(root, 0, p, s)
        res = fix_parens(res + ' (' + x + ')')
        return res

    x = entry[d][p]
    if isinstance(x, str):
        res = lexicon_lookup_(root, d, 0, s)
        res = fix_parens(res + ' (' + x + ')')
        return res

    return entry[d][p][s]

defaults = 'UNI DEL CSL NRM M EXS OBL STA UNFRAMED MNO FAC CTX PRC ASR PPS CNF'.split()

def nice_level(deg, typ):
    return '= > < OPT MIN SPL IFR ≥ ≤'.split()[deg - 1] + {1: 'ᵣ', 2: 'ₐ', 3: '₃'}[typ]

def nice_suffix(s, full_names=False, t3_adjunct=False):
    if t3_adjunct:
        return nice_gloss(s['v3c_adjunct'], full_names)

    if s['code'] == 'LVL':
        return nice_level(int(s['degree'][-1]), int(s['degree'][5]))

    typ = {'1': '', '2': '₂', '3': '₃'}[s['degree'][5]]
    if s['code'] in suffixes:
        # TODO: ₁ ₂?
        return suffixes[s['code']][int(s['degree'][-1]) - 1].join('‘’') + typ
    deg = s['degree'][-1].translate(SUP)
    return s['code'] + typ + deg

def nice_code(key, full_names=False):
    code = key['code']
    if code[:3] in biases and full_names:
         return '*(%s)*' % (biases[code[:3]]['+' in code])
    elif code.startswith('CMP'):
        p = {
            '1': 'previously less',
            '2': 'previously more',
            '3': 'still less',
            '4': 'still more',
            '5': 'now less',
            '6': 'now more',
            '7': 'previously equal',
            '8': 'previous level unknown'
        }[code[3]]
        q = {
            'A': 'but still low',
            'B': 'but now high',
            'C': 'now also high',
        }[code[4]]
        if 'now' in p: q = q.replace('now ', '')
        return '%s[%s; %s]' % (code, p, q)
    levels = 'EQU SUR DFC OPT MIN SPL IFR SPQ SBE'.split()
    if code[:3] in levels:
        return nice_level(levels.index(code[:3]) + 1, 'ra'.index(code[3:]) + 1)
    return key['name'].lower() if full_names else key['code']


def nice_gloss(word, full_names=False):
    word = normalize(word.lower().strip('.,?!'))

    try:
        parse = Factory.parseWord(word)
        desc = parse.fullDescription()
        descType = desc['type']

        if desc['type'] == 'Bias adjunct':
            code = desc['Bias']['code']
            return nice_code(desc['Bias'], full_names)

        if desc['type'] == 'Personal adjunct':
            tags = []
            for k in desc['categories']:
                if k in desc and desc[k]['code'] not in defaults:
                    tags.append(nice_code(desc[k], full_names))
            return '-'.join(tags)

        if desc['type'] != 'Formative':
            tags = []
            for k in desc['categories']:
                if k in desc and desc[k]['code'] not in defaults:
                    tags.append(nice_code(desc[k], full_names))
            return desc['type'] + ': ' + '-'.join(tags)

        tags = []
        root = desc.pop('Root')
        designation = desc.pop('Designation')['code']
        stem_and_pattern = desc.pop('Stem and Pattern', {'code': 'P1S1'})['code']
        lex = lexicon_lookup(root, designation, stem_and_pattern)

        ir = None
        if 'Incorporated root' in desc:
            i_root = desc.pop('Incorporated root')
            i_designation = desc.pop('Designation (inc)')['code']
            i_stem_and_pattern = desc.pop('Stem and Pattern (inc)', {'code': 'P1S1'})['code']
            i_lex = lexicon_lookup(i_root, i_designation, i_stem_and_pattern)
            inc_tags = []
            for k in desc['categories']:
                if k.endswith('(inc)') and k in desc:
                    key = desc.pop(k)
                    if key['code'] not in defaults:
                        inc_tags.append(nice_code(key, full_names))
            ir = '-'.join(["*%s*" % i_lex] + inc_tags)


        for k in desc['categories']:
            if k in desc and desc[k]['code'] not in defaults:
                tags.append(nice_code(desc[k], full_names))
        res = '-'.join(["*%s*" % lex] + tags)
        if ir:
            res += '-[%s]' % ir
        if 'suffixes' in desc:
            t3_adjunct = all(s['degree'][5] == '3' for s in desc['suffixes'])
            res += ' + ' + ' + '.join(nice_suffix(s, full_names, t3_adjunct) for s in desc['suffixes'])

        return res
    except arpeggio.NoMatch as e:
        return "Couldn't parse."
    except AnalysisException as e:
        return str(e)

client = discord.Client()

def bot_result(message_content):
    cmd, *words = message_content.split()
    full_names = 'full' in cmd

    if len(words) == 1:
        return nice_gloss(words[0], full_names)
    else:
        return '\n'.join(['**__Gloss:__**'] + ['**%s**: %s' % (word.lower().strip('.,?!'), nice_gloss(word, full_names)) for word in words])


@client.event
async def on_ready():
    print('Running Discord bot:', client.user)

@client.event
async def on_message(message):
    say = lambda s: client.send_message(message.channel, s)
    if message.author == client.user: return
    if message.content.startswith('!gloss'):
        await say(bot_result(message.content))

if __name__ == '__main__':
    if sys.argv[1:]:
        print(bot_result(' '.join(sys.argv[1:])))
    else:
        client.run(os.getenv('ULAMTON_TOKEN'))
