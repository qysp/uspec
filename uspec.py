#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Inspired by and based on CUPP 3.1.0-alpha (Common User Passwords Profiler)

__author__ = 'qsyp'
__version__ = '2.0.0'
__maintainer__ = 'qsyp'
__program__ = 'USPEC Wordlist Generator'


from datetime import datetime
import configparser
import traceback
import itertools
import argparse
import logging
import sys
import re
import os


CONFIG = dict()
LOGGER = logging.getLogger(__program__)
PATH = os.path.dirname(os.path.abspath(__file__))
NOW = lambda time_format: datetime.now().strftime(time_format)


def setup_logging():
    """Setup the logging handler."""
    level = CONFIG['logging_level'].upper()
    if level not in logging._nameToLevel.keys():
        print(f'[-] Could not set logging level "{level}"!')
        return
    try:
        LOGGER.setLevel(level)
        handler = logging.FileHandler(
            filename='{0}/{1}'.format(PATH, CONFIG['log_file']),
            encoding='utf-8',
            mode=CONFIG['logging_mode']
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter(
            '[{asctime}] [{levelname:<7}] {name}: {message}',
            dt_fmt,
            style='{'
        )
        handler.setFormatter(fmt)
        LOGGER.addHandler(handler)
    except:
        print('[-] An error occured while setting up the logging handler!')


def get_config(filename):
    """Read the configuration file."""
    if not filename:
        filename = os.path.join(PATH, 'uspec.cfg')
    try:
        config = configparser.ConfigParser()
        config.read(filename)
        # Load config into global variable `CONFIG`
        CONFIG.update({
            'length_min':    config.getint('Options','wlen_min'),
            'length_max':    config.getint('Options','wlen_max'),
            'tails':         config.get('Options', 'tails'),
            'leet_chars':    dict(config.items('Leet')),
            'special_chars': config.get('Chars', 'special_chars'),
            'required':      config.getboolean('Chars', 'required'),
            'output_file':   config.get('Output', 'output_file').strip(),
            'merged_file':   config.get('Output', 'merged_file').strip(),
            'logging':       config.getboolean('Logging', 'logging'),
            'log_file':      config.get('Logging', 'log_file'),
            'logging_mode':  config.get('Logging', 'logging_mode'),
            'logging_level': config.get('Logging', 'logging_level')
        })
    except:
        print('[-] An error occured while trying to read the config file.')
        sys.exit(1)


def get_parser():
    """Get the available arguments."""
    arg_parser = argparse.ArgumentParser(
        description=f'{__program__} v{__version__}'
    )
    arg_parser.add_argument('-l', '--leet', action='store_true',
        help='replace letters with predefined numbers or symbols')
    arg_parser.add_argument('-s', '--special', action='store_true',
        help='add special characters to each permutations result')
    arg_parser.add_argument('-t', '--tails', action='store_true',
        help='add number tails to each permutations result')
    arg_parser.add_argument('-r', '--reverse', action='store_true',
        help='reverse entered keywords')
    arg_parser.add_argument('-c', '--case', action='store_true',
        help='treat keyword input case sensitive')
    arg_parser.add_argument('-u', '--upper', action='store_true',
        help='captialize first letter of each permutation result')
    arg_parser.add_argument('-i', '--import',
        metavar='FILENAME', dest='import_file',
        help='enter filename of a list of keywords')
    arg_parser.add_argument('-f', '--config',
        metavar='CONFIG', dest='config_file',
        help='enter filename of config file (default is "uspec.cfg")')
    arg_parser.add_argument('-m', '--merge', metavar='WORDLIST',
        dest='merge_files', nargs='*', type=argparse.FileType('r'),
        help='enter filenames of 2 or more wordlists to merge them')

    return arg_parser


def get_keywords(kws, case):
    """Format keywords and filter empty ones out."""
    keywords = set()
    for kw in kws:
        # Argument: case sensitive
        if case:
            keywords.add(kw.strip())
        else:
            keywords.add(kw.strip().lower())
    return list(filter(None, keywords))


def get_dates(dates):
    """Format dates and create different combinations"""
    tmp = set()
    regex = re.compile(r"""^
        # Day: 01 - 31
        (0[1-9] | 1[0-9] | 2[0-9] | 3[0-1])
        .
        # Month: 01 - 12
        (0[1-9] | 1[0-2])
        .
        # Year: 0000 - 9999
        [0-9]{4}
        $""",
        re.VERBOSE|re.MULTILINE)

    for date in dates.split(','):
        if re.match(regex, date.strip()):
            tmp.add(date.strip())

    if len(tmp) < 1:
        print('\n[-] "Exact dates format" faulty!')
        return None

    # dl -> date list
    dl = list(filter(None, tmp))
    tails = set()

    for date in dl:
        # Example: ['31', '12', '1995']
        nums = date.split('.')
        y = nums[2]
        # 1995, 995, 199, 95
        # seperating them to not create a bunch of useless combinations
        years = [y, y[1:4], y[:3], y[2:4]]
        for year in years:
            comb = nums[:-1]
            comb.append(year)
            for i in range(1, len(comb)+1):
                tails.update(list(permutations(comb, i)))
            tails.update(comb)
    return list(filter(None, tails))


def get_ranges(ranges):
    """Verify and format ranges and filter empty ones out."""
    tails = set()
    # 0 - 9999
    regex = re.compile(r'^([0-9]{1,4})(-)([0-9]{1,4})$')

    if ranges is not None:
        rl = ranges.split(',')
        for r in rl:
            if re.match(regex, r):
                tmp = r.split('-')
                for inc in range(int(tmp[0]), int(tmp[1])+1):
                    tails.add(str(inc))

        if len(tails) < 1:
            print('\n[-] "Range format" faulty!')
            return None

        return list(filter(None, tails))


def reverse_keywords(keywords):
    """Reverse keywords and filter empty ones out (palindromes)."""
    # rs = reversed set
    rs = set()
    for keyword in keywords:
        rs.add(keyword[::-1])
    return list(filter(None, rs))


def permutations(iterable, r=None):
    """Slightly modified version of the itertools permutations fn:
    https://docs.python.org/3/library/itertools.html

    Comments indicate a modification of the original code.
    """
    # ADDED: sort tuple by length of each word
    pool = sorted(tuple(iterable), key=len)
    n = len(pool)
    r = n if r is None else r
    # ADDED: get the max length of all iterable items within the range of `r`
    cap = sum(len(pool[i]) for i in range(r))
    # ADDED: only permutate the iterable if it could be within the boundary
    if r > n or CONFIG['length_max'] < cap:
        return
    indices = list(range(n))
    cycles = list(range(n, n-r, -1))
    # ADDED:
    # - assign permutation result to variable (PEP8)
    # - only yield the result if it's within the boundary
    result = ''.join((tuple(pool[i] for i in indices[:r])))
    if len(str(result)) <= CONFIG['length_max']:
        yield result
    while n:
        for i in reversed(range(r)):
            cycles[i] -= 1
            if cycles[i] == 0:
                indices[i:] = indices[i+1:] + indices[i:i+1]
                cycles[i] = n - i
            else:
                j = cycles[i]
                indices[i], indices[-j] = indices[-j], indices[i]
                result = ''.join((tuple(pool[i] for i in indices[:r])))
                # ADDED: only yield the result if it's within the boundary
                if len(str(result)) <= CONFIG['length_max']:
                    yield result
                break
        else:
            return


def get_permutations(kws, dates):
    """Create permutations and append date combinations."""
    # pl = permutations list
    pl = list()
    if kws is not None:
        if len(kws) > 1:
            LOGGER.debug('[PERMUTATIONS] Starting permutations.')
            for i in range(1, len(kws)+1):
                    for perm in permutations(kws, i):
                        pl.append(perm)
            LOGGER.debug('[PERMUTATIONS] Finished permutations.')
        elif len(kws) == 1:
            for kw in kws:
                pl.append(kw)

    if dates is not None:
        if len(pl) >= 1:
            for perm in range(len(pl)):
                for date in dates:
                    if len(pl[perm] + date) <= CONFIG['length_max']:
                        pl.append(pl[perm] + date)
            LOGGER.debug('Added date tails to permutation results.')
        else:
            for date in dates:
                pl.append(date)
    return pl


def add_specialchars(wordlist):
    """Append special characters to words."""
    chars = list(filter(None, CONFIG['special_chars'].split(',')))
    # sl = special (character) list
    sl = list()
    for word in wordlist:
        for char in chars:
            result = word + char.strip()
            if len(result) <= CONFIG['length_max']:
                sl.append(result)
    return sl


def add_tails(wordlist):
    """Append additional tails to words."""
    tails = list(filter(None, CONFIG['tails'].split(',')))
    # tl = tails list
    tl = list()
    for word in wordlist:
        for tail in tails:
            if len(word + tail.strip()) <= CONFIG['length_max']:
                tl.append(word + tail.strip())
    return tl


def add_leet(wordlist):
    """Extend wordlist with character subtitutions for word."""
    # rl = replacement list
    rl = list()
    wl = wordlist
    lc_keys = CONFIG['leet_chars'].keys()
    for key, item in CONFIG['leet_chars'].items():
        chars = item.split(',')
        for lc in chars:
            """TODO: fix consistency
            Target state:
            - all possible combinations
            Actual state:
            - either '4pple'/'appl3'/'app1e' or '4pp13'
            - no combinations of different leet chars for
              one character (e.g. 4lph@/@lph4 instead of 4alp4 & @lph@)
            """
            # Replace all given characters with substitutions
            wl = [word.replace(key, lc.strip()) for word in wl]
            # Only replace one of the characters with a substitution
            rl.extend(word.replace(key, lc.strip()) for word in wordlist)
    rl.extend(wl)
    return rl


def add_caps(wordlist):
    """Extend wordlist with an uppercase version of the wordlist."""
    # cs = capitalized set
    cs = set()
    for word in wordlist:
        cs.add(word.capitalize())
    return cs


def save_output(wordlist):
    """Save the wordlist to the output file."""
    directory = os.path.join(PATH, 'output')
    output =  '{0}_{1}'.format(
        NOW('%Y-%m-%d_%H-%M-%S'),
        CONFIG['output_file']
    )
    lines = len(wordlist)

    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(os.path.join(directory, output), 'w') as f:
        LOGGER.debug(f'Writing output to file: {output}.')
        f.write('\n'.join(sorted(wordlist)))

    print(f'[+] Successfully written wordlist to output/{output} '
           '(containing {:,} lines).'.format(lines))
    LOGGER.info(f'Successfully written wordlist: {output} '
                 '(containing lines: {:,}).'.format(lines))


def main():
    """Execute utilities based on configurations and given arguments."""
    args = get_parser().parse_args()
    try:
        get_config(args.config_file)
    except (KeyError, configparser.NoSectionError):
        print('\n[-] The config filename or the structure is not correct!')
        sys.exit(1)

    if CONFIG['logging']:
        setup_logging()

    if args.merge_files:
        if len(args.merge_files) >= 2:
            merge_wordlists(args.merge_files)
        else:
            print('\n[-] You must at least enter 2 filenames.')
            LOGGER.debug('Insufficient amount of files to merge supplied.')
            sys.exit(1)
    else:
        generate_wordlist(args)


def generate_wordlist(args):
    """Take user input and manage the wordlist generation."""
    print('[!] Leave the input blank [Enter] to skip the prompt.')

    if args.import_file:
        try:
            LOGGER.debug(f'Trying to use keywords from {args.import_file}.')
            with open(args.import_file, 'r') as f:
                keywords = [keyword for keyword in f]
                LOGGER.debug('Successfully imported words from {0}'.format(
                    args.import_file
                ))
        except FileNotFoundError:
            print('\n[-] Could not find file! Please correct your input.')
            LOGGER.debug('Import file {0} could not be found.'.format(
                args.import_file
            ))
            sys.exit(1)
    else:
        LOGGER.debug('Taking user input for keywords.')
        print("""
Keywords related to the target (comma-separated):
Example: John, Doe, Jane, London, hotdog, dragon""")
        keywords = input('> ').split(',')
        if len(keywords) > 0:
            keywords = get_keywords(keywords, args.case)
            LOGGER.debug(f'Got user input for keywords {keywords}')

    dates = set()
    LOGGER.debug('Taking user input for dates.')
    print("""
Exact dates related to the target (comma-seperated):
Format:  DD.MM.YYYY
Example: 12.04.1982, 20.12.1986, 04.01.2003""")
    exact_dates = input('> ')
    if len(exact_dates) >= 10:
        try:
            dates.update(get_dates(exact_dates))
            LOGGER.debug(f'Got user input for dates {dates}')
        except TypeError as e:
            LOGGER.debug('[DATES] {0}'.format(
                traceback.format_exception_only(type(e), e)
            ))
            pass

    LOGGER.debug('Taking user input for ranges.')
    print("""
Range of numbers related to the target (comma-seperated):
Format:  N[nnn]-N[nnn] (minimum: 0 | maximum: 9999)
Example: 5-23, 87-105, 30-312, 1990-1995""")
    ranges = input('> ')
    if len(ranges) >= 3:
        try:
            dates.update(get_ranges(ranges))
        except TypeError as e:
            LOGGER.debug('[RANGES] {0}'.format(
                traceback.format_exception_only(type(e), e)
            ))
            pass

    if len(dates) == 0 and len(keywords) == 0:
        LOGGER.error('Not enough data provided to generate wordlist.')
        print('\n[-] Not enough data provided to generate a wordlist.')
        sys.exit(1)

    print('\n[+] Generating wordlist. This might take a while...')
    LOGGER.info('Trying to generate wordlist.')
    all_keywords = set(keywords)

    if args.reverse and keywords is not None:
        all_keywords.update(reverse_keywords(keywords))
        LOGGER.debug('Reversed given keywords.')

    wordlist = get_permutations(all_keywords, dates)

    if args.tails:
        wordlist.extend(add_tails(wordlist))
        LOGGER.debug('Added tails to given keywords.')

    if args.special:
        if CONFIG['required']:
            wordlist = add_specialchars(wordlist)
            LOGGER.debug('[REQUIRED] Added special chars to given keywords.')
        else:
            wordlist.extend(add_specialchars(wordlist))
            LOGGER.debug('Added special chars to given keywords.')

    if args.leet and keywords is not None:
        leet_wl = add_leet(wordlist)
        LOGGER.debug('Added leet chars to given keywords.')
        if leet_wl is not None:
            wordlist.extend(leet_wl)

    clean_wordlist = set()
    for word in wordlist:
        if len(word) in range(CONFIG['length_min'], CONFIG['length_max']+1):
            clean_wordlist.add(word)
    LOGGER.debug('Cleaned wordlist from too long/small words.')

    if args.upper:
        clean_wordlist = clean_wordlist | add_caps(clean_wordlist)
        LOGGER.debug('Added uppercase wordlist version.')
    LOGGER.info('Successfully generated wordlist.')

    save_output(clean_wordlist)


def merge_wordlists(merge_files):
    """Merge multiple files together."""
    wordlist = set()
    output =  '{0}_{1}'.format(
        NOW('%Y-%m-%d_%H-%M-%S'),
        CONFIG['merged_file']
    )
    print('\n[+] Merging files...')
    LOGGER.info('Trying to merge files together.')

    for file in merge_files:
        wordlist.update(keyword for keyword in file)
    lines = len(wordlist)

    directory = os.path.join(PATH, 'output')
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(os.path.join(directory, output), 'w') as f:
        LOGGER.debug(f'Writing output to file: {output}')
        f.writelines(sorted(wordlist))

    print(f'[+] Successfully merged files and saved to output/{output} '
        '(containing {:,} lines).'.format(lines))
    LOGGER.info(f'Successfully merged files together: {output} '
        '(containing lines: {:,}).'.format(lines))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n[+] Received keyboard interrupt. Exiting out cleanly...')
        LOGGER.debug(f'Exited {__program__} due to keyboard interrupt.')
        sys.exit(0)
