#!/usr/bin/env python
# coding=latin-1
"""
Copyright (C) 2012-2018: W.G. Vree
Contributions: M. Tarenskeen, N. Liberg, Paul Villiger, Janus Meuris, Larry Myerscough, 
Dick Jackson, Jan Wybren de Jong, Mark Zealey.
Modified by Hannah Einstein, 2022

This program is free software; you can redistribute it and/or modify it under the terms of the
Lesser GNU General Public License as published by the Free Software Foundation;

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the Lesser GNU General Public License for more details. <http://www.gnu.org/licenses/lgpl.html>.
"""

try:
    import xml.etree.cElementTree as E
except:
    import xml.etree.ElementTree as E
import os, sys, types, re, math
from typing import Optional, Tuple, Any

VERSION = 143

python3 = sys.version_info.major > 2
if python3:
    tupletype = tuple
    listtype = list
    max_int = sys.maxsize
else:
    tupletype = types.TupleType  # type: ignore
    listtype = types.ListType  # type: ignore
    max_int = sys.maxint  # type: ignore

note_ornamentation_map = {  # for notations/, modified from EasyABC
    "ornaments/trill-mark": "T",
    "ornaments/mordent": "M",
    "ornaments/inverted-mordent": "P",
    "ornaments/turn": "!turn!",
    "ornaments/inverted-turn": "!invertedturn!",
    "technical/up-bow": "u",
    "technical/down-bow": "v",
    "technical/harmonic": "!open!",
    "technical/open-string": "!open!",
    "technical/stopped": "!plus!",
    "technical/snap-pizzicato": "!snap!",
    "technical/thumb-position": "!thumb!",
    "articulations/accent": "!>!",
    "articulations/strong-accent": "!^!",
    "articulations/staccato": ".",
    "articulations/scoop": "!slide!",
    "fermata": "!fermata!",
    "arpeggiate": "!arpeggio!",
    "articulations/tenuto": "!tenuto!",
    "articulations/staccatissimo": "!wedge!",  # not sure whether this is the right translation
    "articulations/spiccato": "!wedge!",  # not sure whether this is the right translation
    "articulations/breath-mark": "!breath!",  # this may need to be tested to make sure it appears on the right side of the note
    "articulations/detached-legato": "!tenuto!.",
}

dynamics_map = {  # for direction/direction-type/dynamics/
    "p": "!p!",
    "pp": "!pp!",
    "ppp": "!ppp!",
    "pppp": "!pppp!",
    "f": "!f!",
    "ff": "!ff!",
    "fff": "!fff!",
    "ffff": "!ffff!",
    "mp": "!mp!",
    "mf": "!mf!",
    "sfz": "!sfz!",
}

perc_svg = """%%beginsvg
    <defs>
    <text id="x" x="-3" y="0">&#xe263;</text>
    <text id="x-" x="-3" y="0">&#xe263;</text>
    <text id="x+" x="-3" y="0">&#xe263;</text>
    <text id="normal" x="-3.7" y="0">&#xe0a3;</text>
    <text id="normal-" x="-3.7" y="0">&#xe0a3;</text>
    <text id="normal+" x="-3.7" y="0">&#xe0a4;</text>
    <g id="circle-x"><text x="-3" y="0">&#xe263;</text><circle r="4" class="stroke"></circle></g>
    <g id="circle-x-"><text x="-3" y="0">&#xe263;</text><circle r="4" class="stroke"></circle></g>
    <path id="triangle" d="m-4 -3.2l4 6.4 4 -6.4z" class="stroke" style="stroke-width:1.4"></path>
    <path id="triangle-" d="m-4 -3.2l4 6.4 4 -6.4z" class="stroke" style="stroke-width:1.4"></path>
    <path id="triangle+" d="m-4 -3.2l4 6.4 4 -6.4z" class="stroke" style="fill:#000"></path>
    <path id="square" d="m-3.5 3l0 -6.2 7.2 0 0 6.2z" class="stroke" style="stroke-width:1.4"></path>
    <path id="square-" d="m-3.5 3l0 -6.2 7.2 0 0 6.2z" class="stroke" style="stroke-width:1.4"></path>
    <path id="square+" d="m-3.5 3l0 -6.2 7.2 0 0 6.2z" class="stroke" style="fill:#000"></path>
    <path id="diamond" d="m0 -3l4.2 3.2 -4.2 3.2 -4.2 -3.2z" class="stroke" style="stroke-width:1.4"></path>
    <path id="diamond-" d="m0 -3l4.2 3.2 -4.2 3.2 -4.2 -3.2z" class="stroke" style="stroke-width:1.4"></path>
    <path id="diamond+" d="m0 -3l4.2 3.2 -4.2 3.2 -4.2 -3.2z" class="stroke" style="fill:#000"></path>
    </defs>
    %%endsvg"""

tab_svg = """%%beginsvg
    <style type="text/css">
    .bf {font-family:sans-serif; font-size:7px}
    </style>
    <defs>
    <rect id="clr" x="-3" y="-1" width="6" height="5" fill="white"></rect>
    <rect id="clr2" x="-3" y="-1" width="11" height="5" fill="white"></rect>"""

kob_svg = '<g id="head%s" class="bf"><use xlink:href="#clr"></use><text x="-2" y="3">%s</text></g>\n'
kob_svg_2 = '<g id="head%s" class="bf"><use xlink:href="#clr2"></use><text x="-2" y="3">%s</text></g>\n'


def info(string: str, warn=True):
    sys.stderr.write((warn and "-- " or "") + string + "\n")


# -------------------
# data abstractions
# -------------------
class Measure:
    def __init__(self, p):
        self.reset()
        self.ixp = p
        """part number"""
        self.ixm = 0
        """measure number"""
        self.measure_duration = 0
        """measure duration (nominal metre value in divisions)"""
        self.divs = 0
        """number of divisions per 1/4"""
        self.meter = int(4), int(4)

    def reset(self):
        """Reset each measure."""
        self.attr = ""
        """measure signatures, tempo"""
        self.lline = ""
        """left barline, but only holds ':' at start of repeat, otherwise empty"""
        self.rline = "|"
        """right barline"""
        self.lnum = ""
        """(left) volta number"""


class Note:
    def __init__(self, duration=0, n=None):
        self.time = 0  # the time in XML division units
        self.duration = duration  # duration of a note in XML divisions
        self.fact = None  # time modification for tuplet notes (num, div)
        self.tup = [""]  # start(s) and/or stop(s) of tuplet
        self.tupabc = ""  # ABC tuplet string to issue before note
        self.beam = 0  # 1 = beamed
        self.is_grace = False
        self.before = []  # ABC string that goes before the note/chord
        self.after = ""  # the same after the note/chord
        self.notes = n and [n] or []  # notes in the chord
        self.lyrics = {}  # {number -> syllable}
        self.tab = None  # (string number, fret number)
        self.ntdec = ""  # !string!, !courtesy!


class Element:
    def __init__(self, string: str) -> None:
        self.time = 0
        """the time in XML division units"""
        self.string = string
        """any abc string that is not a note"""


class Counter:
    def increment(self, key, voice) -> None:
        self.counters[key][voice] = self.counters[key].get(voice, 0) + 1

    def clear(self, voice_nums) -> None:
        """reset all counters"""
        tups = list(zip(voice_nums, len(voice_nums) * [0]))
        self.counters = {
            "note": dict(tups),
            "nopr": dict(tups),
            "nopt": dict(tups),
        }

    def getv(self, key, voice) -> int:
        return self.counters[key][voice]

    def prcnt(self, ip) -> None:
        """print summary of all non zero counters"""
        for iv in self.counters["note"]:
            if self.getv("nopr", iv) != 0:
                info(
                    "part %d, voice %d has %d skipped non printable notes"
                    % (ip, iv, self.getv("nopr", iv))
                )
            if self.getv("nopt", iv) != 0:
                info(
                    "part %d, voice %d has %d notes without pitch"
                    % (ip, iv, self.getv("nopt", iv))
                )
            if (
                self.getv("note", iv) == 0
            ):  # no real notes counted in this voice
                info("part %d, skipped empty voice %d" % (ip, iv))


class Music:
    def __init__(self, options):
        self.time = 0
        """the current time"""
        self.max_time = 0
        """maximum time in a measure"""
        self.g_measures = []
        """[voices,.. for all measures in a part]"""
        self.g_lyrics = []
        """[{num: (abc_lyric_string, melis)},.. for all measures in a part]"""
        self.voice_nums = set()
        """all used voice id's in a part (XML voice id's == numbers)"""
        self.counter = Counter()
        """global counter object"""
        self.voice_count = 1
        """the global voice count over all parts"""
        self.last_note = None
        """the last real note record inserted in self.voices"""
        self.bars_per_line = options.b
        """the max number of bars per line when writing ABC"""
        self.chars_per_line = options.n
        """the number of chars per line when writing ABC"""
        self.repbra = False
        """true if volta is used somewhere"""
        self.no_volta = options.v
        """no volta on higher voice numbers"""
        self.javascript = options.j
        """compatibility with javascript version"""

    def init_voices(self, new_part=False):
        self.voice_times, self.voices, self.lyrics = {}, {}, {}
        for voice in self.voice_nums:
            self.voice_times[voice] = 0
            # {voice: the end time of the last item in each voice}
            self.voices[voice] = []  # {voice: [Note|Element, ..]}
            self.lyrics[voice] = []  # {voice: [{num: syl}, ..]}
        if new_part:
            self.counter.clear(self.voice_nums)  # clear counters once per part

    def increment_time(self, duration: int):
        self.time += duration
        if self.time < 0:
            self.time = 0  # erroneous <backup> element
        if self.time > self.max_time:
            self.max_time = self.time

    def append_element_voices(self, voices, element):
        for voice in voices:
            self.append_element(voice, element)  # insert element in all voices

    def insert_element(self, voice: int, element: str):
        """insert at the start of voice in the current measure"""
        obj = Element(element)
        obj.time = 0  # because voice is sorted later
        self.voices[voice].insert(0, obj)

    def append_obj(self, voice: int, obj, duration: int):
        obj.time = self.time
        self.voices[voice].append(obj)
        self.increment_time(duration)
        if self.time > self.voice_times[voice]:
            self.voice_times[voice] = self.time
            # don't update for inserted earlier items

    def append_element(self, voice: int, element: str, count=False):
        self.append_obj(voice, Element(element), 0)
        if count:
            self.counter.increment("note", voice)
            # count number of certain elements in each voice (in addition to notes)

    def append_element_at_time(self, voice, element, time):
        """insert element at specified time"""
        obj = Element(element)
        obj.time = time
        self.voices[voice].append(obj)

    def append_note(self, voice: int, note: Note, noot):
        note.notes.append(note.ntdec + noot)
        self.append_obj(voice, note, int(note.duration))
        self.last_note = note
        # remember last note/rest for later modifications (chord, grace)
        if noot != "z" and noot != "x":  # real notes and grace notes
            self.counter.increment(
                "note", voice
            )  # count number of real notes in each voice
            if not note.is_grace:  # for every real note
                self.lyrics[voice].append(
                    note.lyrics
                )  # even when it has no lyrics

    def get_last_record(
        self, voice: int
    ) -> Optional[Element]:  # TODO:figure out
        if self.g_measures:
            return self.g_measures[-1][voice][
                -1
            ]  # the last record in the last measure
        return None  # no previous records in the first measure

    def get_last_melisma(self, voice: int, num) -> bool:
        """get melisma of last measure"""
        if self.g_lyrics:
            lyrdict = self.g_lyrics[-1][
                voice
            ]  # the previous lyrics dict in this voice
            if num in lyrdict:
                return lyrdict[num][
                    1
                ]  # lyrdict = num -> (lyric string, melisma)
        return False  # no previous lyrics in voice or line number

    def add_chord(self, note: Note, noot: str):
        # careful: we assume that chord notes follow immediately
        for d in note.before:  # put all decorations before chord
            if d not in self.last_note.before:
                self.last_note.before += [d]
        self.last_note.notes.append(note.ntdec + noot)

    def add_bar(self, line_break: str, measure: Measure):
        """linebreak, measure data"""
        if (
            measure.measure_duration
            and self.max_time > measure.measure_duration
        ):
            info(
                "measure %d in part %d longer than metre"
                % (measure.ixm + 1, measure.ixp + 1)
            )
        self.time = self.max_time  # the time of the bar lines inserted here
        for voice in self.voice_nums:
            if (
                measure.lline or measure.lnum
            ):  # if left barline or left volta number
                prev = self.get_last_record(
                    voice
                )  # get the previous barline record
                if (
                    prev is not None
                ):  # in measure 1 no previous measure is available
                    x = prev.string  # p.string is the ABC barline string
                    if (
                        measure.lline
                    ):  # append begin of repeat, measure.lline == ':'
                        x = (
                            (x + measure.lline)
                            .replace(":|:", "::")
                            .replace("||", "|")
                        )
                    if self.no_volta == 3:
                        # add volta number only to lowest voice in part 0
                        if measure.ixp + voice == min(self.voice_nums):
                            x += measure.lnum
                    elif measure.lnum:  # new behaviour with I:repbra 0
                        x += measure.lnum
                        # add volta number(s) or text to all voices
                        self.repbra = True  # signal occurrence of a volta
                    prev.string = x  # modify previous right barline
                elif measure.lline:
                    # begin of new part and left repeat bar is required
                    self.insert_element(voice, "|:")
            if line_break:
                prev = self.get_last_record(voice)
                # get the previous barline record
                if prev:
                    prev.string += line_break  # insert linebreak char after the barlines+volta
            if measure.attr:  # insert signatures at front of buffer
                self.insert_element(voice, measure.attr)
            self.append_element(voice, " %s" % measure.rline)
            # insert current barline record at time max_time
            self.voices[voice] = sort_measure(self.voices[voice], measure)
            # make all times consistent
            lyrics = self.lyrics[voice]  # [{number: sylabe}, .. for all notes]
            lyric_dict = {}
            # {number: (abc_lyric_string, melis)} for this voice
            nums = [num for d in lyrics for num in d.keys()]
            # the lyrics numbers in this measure
            max_nums = max(nums + [0])
            # the highest lyrics number in this measure
            for i in range(max_nums, 0, -1):
                xs = [syldict.get(i, "") for syldict in lyrics]
                # collect the syllabi with number i
                melis = self.get_last_melisma(voice, i)
                # get melisma from last measure
                lyric_dict[i] = abc_lyrics(xs, melis)
            self.lyrics[voice] = lyric_dict
            # {number: (abc_lyric_string, melis)} for this measure
            make_broken(self.voices[voice])
        self.g_measures.append(self.voices)
        self.g_lyrics.append(self.lyrics)
        self.time = self.max_time = 0
        self.init_voices()

    def output_voices(self, divs, ip, is_sib: bool):
        """Output all voices of part ip."""
        xml2abcmap = {}  # XML voice number -> abc voice number (one part)
        vnum_keys = list(self.voice_nums)
        if self.javascript or is_sib:
            vnum_keys.sort()
        min_voice = min(vnum_keys or [1])
        # lowest XML voice number of this part
        for voice in vnum_keys:
            if self.counter.getv("note", voice) == 0:
                # no real notes counted in this voice
                continue  # skip empty voices
            if abc_out.denL:
                unit_l = abc_out.denL
                # take the unit length from the -d option
            else:
                unit_l = compute_unit_length(voice, self.g_measures, divs)
                # compute the best unit length for this voice
            abc_out.cmpL.append(unit_l)  # remember for header output
            vn, vl = ([], {})
            # for voice voice: collect all notes to vn and all lyric lines to vl
            for im in range(len(self.g_measures)):
                measure = self.g_measures[im][voice]
                vn.append(out_voice(measure, divs[im], im, ip, unit_l))
                check_melismas(self.g_lyrics, self.g_measures, im, voice)
                for n, (lyric_str, melisma) in self.g_lyrics[im][
                    voice
                ].items():
                    if n in vl:
                        while len(vl[n]) < im:
                            vl[n].append("")  # fill in skipped measures
                        vl[n].append(lyric_str)
                    else:
                        vl[n] = im * [""] + [lyric_str]
                        # must skip im measures
            for (n, lyrics) in vl.items():
                # fill up possibly empty lyric measures at the end
                missing = len(vn) - len(lyrics)
                lyrics += missing * [""]
            abc_out.add(f"V:{self.voice_count}")
            if self.repbra:
                if self.no_volta == 1 and self.voice_count > 1:
                    abc_out.add("I:repbra 0")  # only volta on first voice
                if self.no_volta == 2 and voice > min_voice:
                    abc_out.add("I:repbra 0")
                    # only volta on first voice of each part
            if self.chars_per_line > 0:
                self.bars_per_line = 0
                # option -n (max chars per line) overrules -b (max bars per line)
            elif self.bars_per_line == 0:
                self.chars_per_line = 100  # the default: 100 chars per line
            bar_num = 0  # count bars
            while vn:  # while still measures available
                ib = 1
                chunk = vn[0]
                while ib < len(vn):
                    if (
                        self.chars_per_line > 0
                        and len(chunk) + len(vn[ib]) >= self.chars_per_line
                    ):
                        break  # line full (number of chars)
                    if self.bars_per_line > 0 and ib >= self.bars_per_line:
                        break  # line full (number of bars)
                    chunk += vn[ib]
                    ib += 1
                bar_num += ib
                abc_out.add(f"{chunk} %%{bar_num}")  # line with barnumer
                del vn[:ib]  # chop ib bars
                lyric_lines = sorted(vl.items())
                # order the numbered lyric lines for output
                for n, lyrics in lyric_lines:
                    abc_out.add("w: " + "|".join(lyrics[:ib]) + "|")
                    del lyrics[:ib]
            xml2abcmap[voice] = self.voice_count
            # XML voice number -> ABC voice number
            self.voice_count += 1  # count voices over all parts
        self.g_measures = []  # reset the follwing instance vars for each part
        self.g_lyrics = []
        self.counter.prcnt(ip + 1)
        # print summary of skipped items in this part
        return xml2abcmap


class ABCOutput:
    pagekeys = "scale,pageheight,pagewidth,leftmargin,rightmargin,topmargin,botmargin".split(
        ","
    )

    def __init__(self, name, out_path, X, options):
        self.name = name
        self.abc_out = []
        """list of ABC strings"""
        self.title = "T:Title"
        self.key = "none"
        self.clefs = {}
        """clefs for all abc-voices"""
        self.meter = "none"
        self.tempo = 0
        """0 -> no tempo field"""
        self.tempo_units = (1, 4)
        """note type of tempo direction"""
        self.out_path = out_path
        """the output path or none"""
        self.X = X + 1
        """the ABC tune number"""
        self.denL = options.d
        """denominator of the unit length (L:) from -d option"""
        self.vol_pan = int(options.m)
        """0 -> no %%MIDI, 1 -> only program, 2 -> all %%MIDI"""
        self.cmpL = []  # computed optimal unit length for all voices
        self.javascript = options.j
        """compatibility with javascript version"""
        self.tstep = options.t  # translate perc_map to voicemap
        self.stemless = False  # use U:s=!stemless!
        self.shift_stems = options.s  # shift note heads 3 units left
        if out_path:
            _, base_name = os.path.split(name)
            self.out_file = open(os.path.join(out_path, base_name), "w")
        else:
            self.out_file = sys.stdout
        if self.javascript:
            self.X = 1  # always X:1 in javascript version
        self.pageFmt = {}
        for k in self.pagekeys:
            self.pageFmt[k] = None
        if len(options.p) == 7:
            for k, v in zip(self.pagekeys, options.p):
                try:
                    self.pageFmt[k] = float(v)
                except:
                    info("illegal float %s for %s" % (k, v))
                    continue

    def add(self, string: str) -> None:
        self.abc_out.append(string + "\n")  # collect all ABC output

    def make_header(self, stfmap, partlist, midimap, vmpdct, heads):
        """stfmap = [parts], part = [staves], stave = [voices]"""
        acc_voice, acc_staff, staffs = [], [], stfmap[:]  # staffs is consumed
        for x in partlist:
            # collect partnames into acc_voice and staff groups into acc_staff
            try:
                prgroupelem(x, ("", ""), "", stfmap, acc_voice, acc_staff)
            except:
                info("lousy musicxml: error in part-list")
        staves = " ".join(acc_staff)
        clfnms = {}
        for part, (partname, partabbrv) in zip(staffs, acc_voice):
            if not part:
                continue  # skip empty part
            firstVoice = part[0][0]  # the first voice number in this part
            nm = partname.replace("\n", r"\n").replace(".:", ".").strip(":")
            snm = partabbrv.replace("\n", r"\n").replace(".:", ".").strip(":")
            clfnms[firstVoice] = (nm and 'nm="%s"' % nm or "") + (
                snm and ' snm="%s"' % snm or ""
            )
        hd = ["X:%d\n%s\n" % (self.X, self.title)]
        for i, k in enumerate(self.pagekeys):
            if self.javascript and k in [
                "pageheight",
                "topmargin",
                "botmargin",
            ]:
                continue
            if self.pageFmt[k] is not None:
                hd.append(
                    "%%%%%s %.2f%s\n"
                    % (k, self.pageFmt[k], i > 0 and "cm" or "")
                )
        if staves and len(acc_staff) > 1:
            hd.append("%%score " + staves + "\n")
        tempo = (
            self.tempo
            and "Q:%d/%d=%s\n"
            % (self.tempo_units[0], self.tempo_units[1], self.tempo)
            or ""
        )  # default no tempo field
        d = (
            {}
        )  # determine the most frequently occurring unit length over all voices
        for x in self.cmpL:
            d[x] = d.get(x, 0) + 1
        if self.javascript:
            defLs = sorted(d.items(), key=lambda x: (-x[1], x[0]))
            # when tie (1) sort on key (0)
        else:
            defLs = sorted(d.items(), key=lambda x: -x[1])
        defL = self.denL and self.denL or defLs[0][0]
        # override default unit length with -d option
        hd.append("L:1/%d\n%sM:%s\n" % (defL, tempo, self.meter))
        hd.append("I:linebreak $\nK:%s\n" % self.key)
        if self.stemless:
            hd.append("U:s=!stemless!\n")
        vxs = sorted(vmpdct.keys())
        for vx in vxs:
            hd.extend(vmpdct[vx])
        self.dojef = 0  # translate perc_map to voicemap
        for vnum, clef in self.clefs.items():
            ch, prg, vol, pan = list(midimap[vnum - 1])[:4]
            dmap = list(midimap[vnum - 1])[
                4:
            ]  # map of abc percussion notes to MIDI notes
            print(dmap)
            if dmap and "perc" not in clef:
                clef = (clef + " map=perc").strip()
            hd.append("V:%d %s %s\n" % (vnum, clef, clfnms.get(vnum, "")))
            if vnum in vmpdct:
                hd.append("%%%%voicemap tab%d\n" % vnum)
                hd.append(
                    "K:none\nM:none\n%%clef none\n%%staffscale 1.6\n%%flatbeams true\n%%stemdir down\n"
                )
            if "perc" in clef:
                hd.append("K:none\n")
                # no key for a perc voice
            if self.vol_pan > 1:
                # option -m 2 -> output all recognized MIDI commands when needed and present in XML
                if ch > 0 and ch != vnum:
                    hd.append("%%%%MIDI channel %d\n" % ch)
                if prg > 0:
                    hd.append("%%%%MIDI program %d\n" % (prg - 1))
                if vol >= 0:
                    hd.append("%%%%MIDI control 7 %.0f\n" % vol)
                    # volume == 0 is possible ...
                if pan >= 0:
                    hd.append("%%%%MIDI control 10 %.0f\n" % pan)
            elif self.vol_pan > 0:
                # default -> only output MIDI program command when present in XML
                if dmap and ch > 0:
                    hd.append("%%%%MIDI channel %d\n" % ch)
                    # also channel if percussion part
                if prg > 0:
                    hd.append("%%%%MIDI program %d\n" % (prg - 1))
            for abcNote, step, midiNote, notehead in dmap:
                if not notehead:
                    notehead = "normal"
                if abc_to_midi_pitch(abcNote) != midiNote or abcNote != step:
                    if self.vol_pan > 0:
                        hd.append(
                            "%%%%MIDI drummap %s %s\n" % (abcNote, midiNote)
                        )
                    hd.append(
                        "I:perc_map %s %s %s %s\n"
                        % (abcNote, step, midiNote, notehead)
                    )
                    self.dojef = self.tstep
            if defL != self.cmpL[vnum - 1]:
                # only if computed unit length different from header
                hd.append("L:1/%d\n" % self.cmpL[vnum - 1])
        self.abc_out = hd + self.abc_out
        if heads:  # output SVG stuff needed for tablature
            k1 = kob_svg.replace("-2", "-5") if self.shift_stems else kob_svg
            # shift note heads 3 units left
            k2 = (
                kob_svg_2.replace("-2", "-5")
                if self.shift_stems
                else kob_svg_2
            )
            tb = tab_svg.replace("-3", "-6") if self.shift_stems else tab_svg
            ks = sorted(heads.keys())  # javascript compatibility
            ks = [k2 % (k, k) if len(k) == 2 else k1 % (k, k) for k in ks]
            tbs = list(map(lambda x: x.strip() + "\n", tb.splitlines()))
            # javascript compatibility
            self.abc_out = tbs + ks + ["</defs>\n%%endsvg\n"] + self.abc_out

    def write_all(self):
        """determine the required encoding of the entire ABC output"""
        string = "".join(self.abc_out)
        if self.dojef:
            string = perc2map(string)
        if python3:
            self.out_file.write(string)
        else:
            self.out_file.write(string.encode("utf-8"))  # type: ignore
        if self.out_path:
            self.out_file.close()  # close each file with -o option
        else:
            self.out_file.write("\n")  # add empty line between tunes on stdout
        info(
            "%s written with %d voices" % (self.name, len(self.clefs)),
            warn=False,
        )


# ----------------
# functions
# ----------------
def abc_lyrics(lyrics: list[str], melisma: bool):
    """Convert list xs to ABC lyrics."""
    if not "".join(lyrics):
        return "", False  # there is no lyrics in this measure
    res = []
    for (
        lyric
    ) in lyrics:  # xs has for every note a lyrics syllable or an empty string
        if lyric == "":  # note without lyrics
            if melisma:
                lyric = "_"  # set melisma
            else:
                lyric = "*"  # skip note
        elif lyric.endswith("_") and not lyric.endswith(
            r"\_"
        ):  # start of new melisma
            lyric = lyric.replace("_", "")  # remove and set melisma boolean
            melisma = True  # so next skips will become melisma
        else:
            melisma = False  # melisma stops on first syllable
        res.append(lyric)
    return (" ".join(res), melisma)


def simplify(a: int, b: int) -> Tuple[int, int]:
    """Divide a and b by their greatest common divisor."""
    x, y = a, b
    while b:
        a, b = b, a % b
    return x // a, y // a


def abc_duration(nx: Note, divs: int, unit_l: int) -> str:
    """convert an MusicXML duration d to abc units with L:1/unit_l"""
    if nx.duration == 0:
        return ""  # when called for elements without duration
    num, den = simplify(
        unit_l * nx.duration, divs * 4
    )  # L=1/8 -> unit_l = 8 units
    if nx.fact:  # apply tuplet time modification
        numfac, denfac = nx.fact
        num, den = simplify(num * numfac, den * denfac)
    if den > 64:  # limit the denominator to a maximum of 64
        x = float(num) / den
        n = math.floor(x)
        # when just above an integer n
        if x - n < 0.1 * x:
            num, den = n, 1
            # round to n
        num64 = 64.0 * num / den + 1.0e-15  # to get Python2 behaviour of round
        num, den = simplify(int(round(num64)), 64)
    if num == 1:
        if den == 1:
            dabc = ""
        elif den == 2:
            dabc = "/"
        else:
            dabc = "/%d" % den
    elif den == 1:
        dabc = "%d" % num
    else:
        dabc = "%d/%d" % (num, den)
    return dabc


def abc_to_midi_pitch(note: str) -> int:
    """abc note -> MIDI pitch"""
    r = re.search(r"([_^]*)([A-Ga-g])([',]*)", note)
    if not r:
        return -1
    acc, note, octave = r.groups()
    nUp = n.upper()
    p = (
        60
        + [0, 2, 4, 5, 7, 9, 11]["CDEFGAB".index(nUp)]
        + (12 if nUp != n else 0)
    )
    if acc:
        p += (1 if acc[0] == "^" else -1) * len(acc)
    if oct:
        p += (12 if octave[0] == "'" else -12) * len(octave)
    return p


def staff_step(ptc: str, octave: int, clef: str, tabStep: bool) -> str:
    ndif = 0
    if "staff_lines=1" in clef:
        ndif += 4  # meaning of one line: E (XML) -> B (ABC)
    if not tabStep and clef.startswith("bass"):
        ndif += 12  # transpose bass -> treble (C3 -> A4)
    if ndif:  # diatonic transposition == addition modulo 7
        nm7 = str("C,D,E,F,G,A,B").split(",")
        n = nm7.index(ptc) + ndif
        ptc, o = nm7[n % 7], octave + n // 7
    if octave > 4:
        ptc = ptc.lower()
    if octave > 5:
        ptc = ptc + (octave - 5) * "'"
    if octave < 4:
        ptc = ptc + (4 - octave) * ","
    return ptc


def set_key(fifths: int, mode: str) -> dict[str, int]:
    sharpness = [
        "Fb",
        "Cb",
        "Gb",
        "Db",
        "Ab",
        "Eb",
        "Bb",
        "F",
        "C",
        "G",
        "D",
        "A",
        "E",
        "B",
        "F#",
        "C#",
        "G#",
        "D#",
        "A#",
        "E#",
        "B#",
    ]
    offTab = {
        "maj": 8,
        "ion": 8,
        "m": 11,
        "min": 11,
        "aeo": 11,
        "mix": 9,
        "dor": 10,
        "phr": 12,
        "lyd": 7,
        "loc": 13,
        "non": 8,
    }
    mode = mode.lower()[:3]  # only first three chars, no case
    key = sharpness[offTab[mode] + fifths] + (
        mode if offTab[mode] != 8 else ""
    )
    accs = ["F", "C", "G", "D", "A", "E", "B"]
    if fifths >= 0:
        msralts = dict(zip(accs[:fifths], fifths * [1]))
    else:
        msralts = dict(zip(accs[fifths:], -fifths * [-1]))
    return key, msralts


def ins_tuplet(ix, notes, fact):
    """read one nested tuplet"""
    tuplet_count = 0
    nx = notes[ix]
    if "start" in nx.tup:
        nx.tup.remove("start")  # do recursive calls when starts remain
    tix = ix  # index of first tuplet note
    fn, fd = fact  # XML time-mod of the higher level
    fnum, fden = nx.fact  # XML time-mod of the current level
    tupfact = fnum // fn, fden // fd  # ABC time mod of this level
    while ix < len(notes):
        nx = notes[ix]
        if isinstance(nx, Element) or nx.is_grace:
            ix += 1  # skip all non tuplet elements
            continue
        if len(nx.tup) > 1:
            print(nx.tup)
        if "start" in nx.tup:  # more nested tuplets to start
            ix, tupcntR = ins_tuplet(
                ix, notes, tupfact
            )  # ix is on the stop note!
            tuplet_count += tupcntR
        elif nx.fact:
            tuplet_count += 1  # count tuplet elements
        if "stop" in nx.tup:
            nx.tup.remove("stop")
            break
        if not nx.fact:  # stop on first non tuplet note
            ix = lastix  # back to last tuplet note
            break
        lastix = ix
        ix += 1
    # put ABC tuplet notation before the recursive ones
    tup = (tupfact[0], tupfact[1], tuplet_count)
    if tup == (3, 2, 3):
        tupPrefix = "(3"
    else:
        tupPrefix = "(%d:%d:%d" % tup
    notes[tix].tupabc = tupPrefix + notes[tix].tupabc
    return ix, tuplet_count  # ix is on the last tuplet note


def make_broken(voice):
    """introduce broken rhythms (voice: one voice, one measure)"""
    voice = [n for n in voice if isinstance(n, Note)]
    i = 0
    while i < len(voice) - 1:
        n1, n2 = voice[i], voice[i + 1]  # scan all adjacent pairs
        # skip if note in tuplet or has no duration or outside beam
        if not n1.fact and not n2.fact and n1.duration > 0 and n2.beam:
            if n1.duration * 3 == n2.duration:
                n2.duration = (2 * n2.duration) // 3
                n1.duration = n1.duration * 2
                n1.after = "<" + n1.after
                i += 1  # do not chain broken rhythms
            elif n2.duration * 3 == n1.duration:
                n1.duration = (2 * n1.duration) // 3
                n2.duration = n2.duration * 2
                n1.after = ">" + n1.after
                i += 1  # do not chain broken rhythms
        i += 1


def out_voice(measure, divs: int, im: int, ip: int, unit_l: int) -> str:
    """note/element objects of one measure in one voice"""
    ix = 0
    while ix < len(measure):  # set all (nested) tuplet annotations
        nx = measure[ix]
        if isinstance(nx, Note) and nx.fact and not nx.is_grace:
            ix, tup_count = ins_tuplet(
                ix, measure, (1, 1)
            )  # read one tuplet, insert annotation(s)
        ix += 1
    vs = []
    for nx in measure:
        if isinstance(nx, Note):
            dur_str = abc_duration(
                nx, divs, unit_l
            )  # XML -> ABC duration string
            is_chord = len(nx.notes) > 1
            cNotes = [nt[:-1] for nt in nx.notes if nt.endswith("-")]
            tie = ""
            if is_chord and len(cNotes) == len(
                nx.notes
            ):  # all chord notes tied
                nx.notes = cNotes  # chord notes without tie
                tie = "-"  # one tie for whole chord
            s = nx.tupabc + "".join(nx.before)
            if is_chord:
                s += "["
            for nt in nx.notes:
                s += nt
            if is_chord:
                s += "]" + tie
            if s.endswith("-"):
                s, tie = s[:-1], "-"  # split off tie
            s += dur_str + tie  # and put it back again
            s += nx.after
            nospace = nx.beam
        else:
            if isinstance(nx.string, listtype):
                nx.string = nx.string[0]
            s = nx.string
            nospace = 1
        if nospace:
            vs.append(s)
        else:
            vs.append(" " + s)
    vs = "".join(vs)  # ad hoc: remove multiple pedal directions
    while vs.find("!ped!!ped!") >= 0:
        vs = vs.replace("!ped!!ped!", "!ped!")
    while vs.find("!ped-up!!ped-up!") >= 0:
        vs = vs.replace("!ped-up!!ped-up!", "!ped-up!")
    while vs.find("!8va(!!8va)!") >= 0:
        vs = vs.replace("!8va(!!8va)!", "")  # remove empty ottava's
    return vs


def sort_measure(voice, measure):
    voice.sort(key=lambda o: o.time)  # sort on time
    time = 0
    v = []
    rests = []  # holds rests in between notes
    for i, nx in enumerate(voice):  # establish sequentiality
        if nx.time > time and check_bug(nx.time - time, measure):
            v.append(Note(nx.time - time, "x"))  # fill hole with invisble rest
            rests.append(len(v) - 1)
        if isinstance(nx, Element):
            if nx.time < time:
                nx.time = (
                    time  # shift elems without duration to where they fit
                )
            v.append(nx)
            time = nx.time
            continue
        if nx.time < time:  # overlapping element
            if nx.notes[0] == "z":
                continue  # discard overlapping rest
            if v[-1].time <= nx.time:  # we can do something
                if v[-1].notes[0] == "z":  # shorten rest
                    v[-1].duration = nx.time - v[-1].time
                    if v[-1].duration == 0:
                        del v[-1]  # nothing left
                    info(
                        "overlap in part %d, measure %d: rest shortened"
                        % (measure.ixp + 1, measure.ixm + 1)
                    )
                else:  # make a chord of overlap
                    v[-1].notes += nx.notes
                    info(
                        "overlap in part %d, measure %d: added chord"
                        % (measure.ixp + 1, measure.ixm + 1)
                    )
                    nx.duration = (nx.time + nx.duration) - time  # the remains
                    if nx.duration <= 0:
                        continue  # nothing left
                    nx.time = time  # append remains
            else:  # give up
                info(
                    "overlapping notes in one voice! part %d, measure %d, note %s discarded"
                    % (
                        measure.ixp + 1,
                        measure.ixm + 1,
                        isinstance(nx, Note) and nx.notes or nx.string,
                    )
                )
                continue
        v.append(nx)
        if isinstance(nx, Note):
            if nx.notes[0] in "zx":
                rests.append(len(v) - 1)  # remember rests between notes
            elif len(rests):
                if nx.beam and not nx.is_grace:  # copy beam into rests
                    for restI in rests:
                        v[restI].beam = nx.beam
                rests = []  # clear rests on each note
        else:
            raise ValueError(
                f"Object {nx} of type {type(nx)} isn't a note or element!"
            )
        time = nx.time + nx.duration
    #   when a measure contains no elements and no forwards -> no increment_time -> self.max_time = 0 -> right barline
    #   is inserted at time == 0 (in addbar) and is only element in the voice when sort_measure is called
    if time == 0:
        info(
            "empty measure in part %d, measure %d, it should contain at least a rest to advance the time!"
            % (measure.ixp + 1, measure.ixm + 1)
        )
    return v


def get_part_list(parts):
    """correct part-list (from buggy XML-software)"""
    xs = []  # the corrected part-list
    e = []  # stack of opened part-groups
    for x in list(parts):  # insert missing stops, delete double starts
        if x.tag == "part-group":
            num, type = x.get("number"), x.get("type")
            if type == "start":
                if num in e:  # missing stop: insert one
                    xs.append(E.Element("part-group", number=num, type="stop"))
                    xs.append(x)
                else:  # normal start
                    xs.append(x)
                    e.append(num)
            else:
                if num in e:  # normal stop
                    e.remove(num)
                    xs.append(x)
                else:
                    pass  # double stop: skip it
        else:
            xs.append(x)
    for num in reversed(e):  # fill missing stops at the end
        xs.append(E.Element("part-group", number=num, type="stop"))
    return xs


def parse_parts(xs: list[E.Element], d: dict[str, list[str]], e):
    """-> [elems on current level], rest of xs"""
    if not xs:
        return [], []
    x = xs.pop(0)
    if x.tag == "part-group":
        num, type = x.get("number", "-"), x.get("type")
        if type == "start":  # go one level deeper
            s = [
                x.findtext(n, "")
                for n in [
                    "group-symbol",
                    "group-barline",
                    "group-name",
                    "group-abbreviation",
                ]
            ]
            d[num] = s  # remember groupdata by group number
            e.append(num)  # make stack of open group numbers
            elemsnext, rest1 = parse_parts(xs, d, e)
            # parse one level deeper to next stop
            elems, rest2 = parse_parts(rest1, d, e)
            # parse the rest on this level
            return [elemsnext] + elems, rest2
        else:  # stop: close level and return group-data
            nums = e.pop()  # last open group number in stack order
            if xs and xs[0].get("type") == "stop":  # two consequetive stops
                if num != nums:  # in the wrong order (tempory solution)
                    d[nums], d[num] = (d[num], d[nums])
                    # exchange values    (only works for two stops!!!)
            sym = d[num]
            # retrieve an return groupdata as last element of the group
            return [sym], xs
    else:
        elems, rest = parse_parts(xs, d, e)
        # parse remaining elements on current level
        name = x.findtext("part-name", ""), x.findtext("part-abbreviation", "")
        return [name] + elems, rest


def brace_part(part: list[list[int]]):
    """Put a brace on multistaff part and group voices."""
    if not part:
        return []  # empty part in the score
    brace = []
    for ivs in part:
        if len(ivs) == 1:  # stave with one voice
            brace.append(str(ivs[0]))
        else:  # stave with multiple voices
            brace += ["(", *list(map(str, ivs)), ")"]
        brace.append("|")
    del brace[-1]  # no barline at the end
    if len(part) > 1:
        brace = ["{", *brace, "}"]
    return brace


def prgroupelem(x, gnm, bar, pmap, acc_voice, acc_staff):
    """collect partnames (acc_voice) and %%score map (acc_staff)"""
    if type(x) == tupletype:  # partname-tuple = (part-name, part-abbrev)
        y = pmap.pop(0)
        if gnm[0]:
            x = [n1 + ":" + n2 for n1, n2 in zip(gnm, x)]
            # put group-name before part-name
        acc_voice.append(x)
        acc_staff.extend(brace_part(y))
    elif len(x) == 2 and type(x[0]) == tupletype:
        # misuse of group just to add extra name to stave
        y = pmap.pop(0)
        nms = [n1 + ":" + n2 for n1, n2 in zip(x[0], x[1][2:])]
        # x[0] = partname-tuple, x[1][2:] = groupname-tuple
        acc_voice.append(nms)
        acc_staff.extend(brace_part(y))
    else:
        prgrouplist(x, bar, pmap, acc_voice, acc_staff)


def prgrouplist(x, pbar, pmap, acc_voice, acc_staff):
    """Collect partnames, scoremap for a part-group."""
    sym, bar, gnm, gabbr = x[
        -1
    ]  # bracket symbol, continue barline, group-name-tuple
    bar = bar == "yes" or pbar  # pbar -> the parent has bar
    acc_staff.append(sym == "brace" and "{" or "[")
    for z in x[:-1]:
        prgroupelem(z, (gnm, gabbr), bar, pmap, acc_voice, acc_staff)
        if bar:
            acc_staff.append("|")
    if bar:
        del acc_staff[-1]  # remove last one before close
    acc_staff.append(sym == "brace" and "}" or "]")


def compute_unit_length(iv: int, measures, divs) -> int:
    """Compute optimal unit length."""
    uLmin, min_len = 0, max_int
    for unit_l in [4, 8, 16]:  # try 1/4, 1/8 and 1/16
        vLen = 0  # total length of ABC duration strings in this voice
        for im, measure in enumerate(measures):  # all measures
            for e in measure[iv]:  # all notes in voice iv
                if isinstance(e, Element) or e.duration == 0:
                    continue  # no real durations
                vLen += len(abc_duration(e, divs[im], unit_l))
                # add len of duration string
        if vLen < min_len:
            uLmin, min_len = unit_l, vLen  # remember the smallest
    return uLmin


def do_syllable(syl: E.Element) -> str:
    text = ""
    for e in syl:
        if e.tag == "elision":
            text += "~"
        elif e.tag == "text":  # escape - and space characters
            text += (
                (e.text or "")
                .replace("_", r"\_")
                .replace("-", r"\-")
                .replace(" ", "~")
            )
    if not text:
        return text
    if syl.findtext("syllabic") in ["begin", "middle"]:
        text += "-"
    if syl.find("extend") is not None:
        text += "_"
    return text


def check_melismas(lyrics, measures, im: int, iv: int):
    if im == 0:
        return
    measure = measures[im][iv]  # notes of the current measure
    cur_lyric = lyrics[im][iv]  # lyrics dict of current measure
    prv_lyric = lyrics[im - 1][iv]  # lyrics dict of previous measure
    for n, (lyric_str, melisma) in prv_lyric.items():
        # all lyric numbers in the previous measure
        if n not in cur_lyric and melisma:
            # melisma required, but no lyrics present -> make one!
            ms = get_melisma(measure)  # get a melisma for the current measure
            if ms:
                cur_lyric[n] = (ms, 0)
                # set melisma as the n-th lyrics of the current measure


def get_melisma(measure):
    """Get melisma from notes in measure."""
    ms = []
    for note in measure:  # every note should get an underscore
        if not isinstance(note, Note):
            continue  # skip Elements
        if note.is_grace:
            continue  # skip grace notes
        if note.notes[0] in "zx":
            break  # stop on first rest
        ms.append("_")
    return " ".join(ms)


def perc2map(abc_in):
    fillmap = {"diamond": 1, "triangle": 1, "square": 1, "normal": 1}
    abc = list(map(lambda x: x.strip(), perc_svg.splitlines()))
    id = "default"
    maps = {"default": []}
    dmaps = {"default": []}
    r1 = re.compile(r"V:\s*(\S+)")
    lines = abc_in.splitlines()
    for x in lines:
        if "I:perc_map" in x:
            noot, step, midi, head = map(lambda x: x.strip(), x.split()[1:])
            if head in fillmap:
                head = head + "+" + "," + head
            x = "%%%%map perc%s %s print=%s midi=%s heads=%s" % (
                id,
                noot,
                step,
                midi,
                head,
            )
            maps[id].append(x)
        if "%%MIDI" in x:
            dmaps[id].append(x)
        if "V:" in x:
            r = r1.match(x)
            if r:
                id = r.group(1)
                if id not in maps:
                    maps[id] = []
                    dmaps[id] = []
    ids = sorted(maps.keys())
    for id in ids:
        abc += maps[id]
    id = "default"
    for x in lines:
        if "I:perc_map" in x:
            continue
        if "%%MIDI" in x:
            continue
        if "V:" in x or "K:" in x:
            r = r1.match(x)
            if r:
                id = r.group(1)
            abc.append(x)
            if id in dmaps and len(dmaps[id]) > 0:
                abc.extend(dmaps[id])
                del dmaps[id]
            if "perc" in x and "map=" not in x:
                x += " map=perc"
            if "map=perc" in x and len(maps[id]) > 0:
                abc.append("%%voicemap perc" + id)
            if "map=off" in x:
                abc.append("%%voicemap")
        else:
            abc.append(x)
    return "\n".join(abc) + "\n"


def add_octave(ptc: str, octave: int) -> str:
    """XML staff step, XML octave number"""
    p = ptc
    if octave > 4:
        p = ptc.lower()
    if octave > 5:
        p = p + (octave - 5) * "'"
    if octave < 4:
        p = p + (4 - octave) * ","
    return p  # ABC pitch == ABC note without accidental


def check_bug(dt, measure):
    if dt > measure.divs / 16:
        return True  # duration should be > 1/64 note
    info(
        "MuseScore bug: incorrect duration, smaller then 1/64! in measure %d, part %d"
        % (measure.ixm, measure.ixp)
    )
    return False


# ----------------
# parser
# ----------------
class Parser:
    note_alts = [  # 3 alternative notations of the same note for tablature mapping
        [
            x.strip()
            for x in "=C,  ^C, =D, ^D, =E, =F, ^F, =G, ^G, =A, ^A, =B".split(
                ","
            )
        ],
        [
            x.strip()
            for x in "^B,  _D,^^C, _E, _F, ^E, _G,^^F, _A,^^G, _B, _C".split(
                ","
            )
        ],
        [
            x.strip()
            for x in "__D,^^B,__E,__F,^^D,__G,^^E,__A,_/A,__B,__C,^^A".split(
                ","
            )
        ],
    ]
    step_map = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    slur_buffer: dict[str, Tuple[str, int, Note, bool]]
    """dict of open slurs keyed by slur number"""
    dirStk: dict[str, Tuple]
    """{direction-type + number -> (type, voice | time)} dict for proper closing"""
    is_in_grace: bool
    """marks a sequence of grace notes"""
    music: Music
    """global music data abstraction"""
    unfold: bool
    """turn unfolding repeats on"""
    ctf: int
    """credit text filter level"""
    g_staff_map: list[list[int]]
    """[[ABC voice numbers] for all parts]"""
    midi_map: list[int]
    """MIDI-settings for each ABC voice, in order"""
    drum_instr: dict[str, int]
    """instr_id -> MIDI pitch for channel 10 notes"""
    drum_notes: dict
    """(XML voice, ABC note) -> (MIDI note, note head)"""
    instr_midis: list[dict[str, list[int]]]
    """[{instr id -> MIDI-settings} for all parts]"""
    midi_defaults: list[int]
    """default MIDI settings for channel, program, volume, panning"""

    def __init__(self, options):
        """unfold repeats, number of chars per line, credit filter level, volta option"""
        self.slur_buffer = {}
        self.dirStk = {}
        self.is_in_grace = False
        self.music = Music(options)
        self.unfold = options.u
        self.ctf = options.c
        self.g_staff_map = []
        self.midi_map = []
        self.drum_instr = {}
        self.drum_notes = {}
        self.instr_midis = []
        self.midi_defaults = [-1, -1, -1, -91]
        self.msralts = {}
        """ml-notenames (without octave) with accidentals from the key"""
        self.cur_alts = {}
        """abc-notenames (with voice number) with passing accidentals"""
        self.staff_map = {}
        """XML staff number -> [XML voice number]"""
        self.voice2staff = {}
        """XML voice number -> allocated staff number"""
        self.clef_map = {}
        """XML staff number -> ABC clef (for header only)"""
        self.cur_clefs = {}
        """XML staff number -> current ABC clef"""
        self.stem_dirs = {}
        """XML voice number -> current stem direction"""
        self.clef_octaves = {}
        """XML staff number -> current clef-octave-change"""
        self.cur_staffs = {}
        """XML voice number -> current XML staff number"""
        self.nolbrk = options.x
        """generate no linebreaks ($)"""
        self.javascript = options.j
        """compatibility with javascript version"""
        self.ornaments = sorted(note_ornamentation_map.items())
        self.format_page = len(options.p) == 1
        """translate XML page format"""
        self.tstep = options.t
        """clef determines step on staff (percussion)"""
        self.dirtov1 = options.v1  #
        """all directions to first voice of staff"""
        self.render_pedal_dirs = options.ped
        """render pedal directions"""
        self.write_stems = options.stm
        """translate stem elements"""
        self.pedal_dir_voice = None
        """voice for pedal directions"""
        self.repeat_str = {}
        """staff number -> [measure number, repeat-text]"""
        self.tab_voice_map = {}
        """ABC voice num -> [%%map ...] for tab voices"""
        self.heads = {}
        """noteheads needed for %%map"""

    def match_slur(
        self,
        type2: str,
        num: Optional[str],
        voice2: int,
        note2: Note,
        is_grace: bool,
        stop_grace: bool,
    ) -> None:
        """Match slur number n in voice v2, add ABC code to before/after."""
        if type2 not in ["start", "stop"]:
            return  # slur type continue has no ABC equivalent
        if num is None:
            num = "1"
        if num in self.slur_buffer:
            type1, voice1, note1, grace1 = self.slur_buffer[n]
            if type2 != type1:  # slur complete, now check the voice
                if (
                    voice2 == voice1
                ):  # begins and ends in the same voice: keep it
                    if type1 == "start" and (not grace1 or not stop_grace):
                        # normal slur: start before stop and no grace slur
                        note1.before = [
                            "("
                        ] + note1.before  # keep left-right order!
                        note2.after += ")"
                    # no else: don't bother with reversed stave spanning slurs
                del self.slur_buffer[n]  # slur finished, remove from stack
            else:  # double definition, keep the last
                info(
                    "double slur numbers %s-%s in part %d, measure %d, voice %d note %s, first discarded"
                    % (
                        type2,
                        n,
                        self.measure.ixp + 1,
                        self.measure.ixm + 1,
                        voice2,
                        note2.notes,
                    )
                )
                self.slur_buffer[n] = (type2, voice2, note2, is_grace)
        else:  # unmatched slur, put in dict
            self.slur_buffer[n] = (type2, voice2, note2, is_grace)

    def do_notations(self, note: Note, notation: E.Element, is_tab: bool):
        for key, val in self.ornaments:
            if notation.find(key) is not None:
                note.before += [val]  # just concat all ornaments
        tremolo = notation.find("ornaments/tremolo")
        if tremolo is not None:
            type = tremolo.get("type")
            if type == "single":
                note.before.insert(0, "!%s!" % (int(tremolo.text) * "/"))
            else:
                note.fact = None  # no time modification in ABC
                if self.tstep:  # abc2svg version
                    if type == "stop":
                        note.before.insert(0, "!trem%s!" % tremolo.text)
                else:  # abc2xml version
                    if type == "start":
                        note.before.insert(
                            0, "!%s-!" % (int(tremolo.text) * "/")
                        )
        fingering = notation.findall("technical/fingering")
        if is_tab:
            string = notation.find("technical/string")
            if string is not None:
                if self.tstep:
                    fret = notation.find("technical/fret")
                    if fret is not None:
                        note.tab = (string.text, fret.text)
                else:
                    deco = (
                        "!%s!" % string.text
                    )  # no double string decos (bug in musescore)
                    if deco not in note.ntdec:
                        note.ntdec += deco
        else:
            for finger in fingering:  # handle multiple finger annotations
                note.before += ["!%s!" % finger.text]
                # fingering goes before chord (add_chord)

        wvln = notation.find("ornaments/wavy-line")
        if wvln is not None:
            if wvln.get("type") == "start":
                note.before = [
                    "!trill(!"
                ] + note.before  # keep left-right order!
            elif wvln.get("type") == "stop":
                note.before = ["!trill)!"] + note.before
        glis = notation.find("glissando")
        if glis is None:
            glis = notation.find("slide")  # treat slide as glissando
        if glis is not None:
            lt = "~" if glis.get("line-type") == "wavy" else "-"
            if glis.get("type") == "start":
                note.before = [
                    "!%s(!" % lt
                ] + note.before  # keep left-right order!
            elif glis.get("type") == "stop":
                note.before = ["!%s)!" % lt] + note.before

    def tab_note(
        self, alt: int, ptc: str, octave: int, voice: int, ntrec: Note
    ):
        p = self.step_map[ptc] + alt  # p in -2 .. 13
        if p > 11:
            octave += 1  # octave correction
        elif p < 0:
            octave -= 1
        p = p % 12  # remap p into 0..11
        (
            snaar_nw,
            fret_nw,
        ) = ntrec.tab  # the computed/annotated allocation of nt
        for i in range(4):  # support same note on 4 strings
            na = self.note_alts[i][
                p
            ]  # get alternative representation of same note
            o = octave
            if na in ["^B", "^^B"]:
                o -= 1  # because in adjacent octave
            if na in ["_C", "__C"]:
                o += 1
            if "/" in na or i == 3:
                o = 9  # emergency notation for 4th string case
            nt = add_octave(na, o)
            string, fret = self.tab_map.get((voice, nt), ("", ""))
            # the current allocation of nt
            if not string:
                break  # note not yet allocated
            if snaar_nw == string:
                return nt  # use present allocation
            if i == 3:  # new allocaion needed but none is free
                fmt = "rejected: voice %d note %3s string %s fret %2s remains: string %s fret %s"
                info(fmt % (voice, nt, snaar_nw, fret_nw, string, fret), True)
                ntrec.tab = (string, fret)
        self.tab_map[voice, nt] = ntrec.tab
        # for tablature map (voice, note) -> (string, fret)
        return nt  # ABC code always in key C (with MIDI pitch alterations)

    def abc_notation(
        self,
        ptc: str,
        octave: int,
        note: E.Element,
        voice: int,
        ntrec: Note,
        is_tab: bool,
    ) -> str:
        """pitch, octave -> ABC notation"""
        acc2alt = {
            "double-flat": -2,
            "flat-flat": -2,
            "flat": -1,
            "natural": 0,
            "sharp": 1,
            "sharp-sharp": 2,
            "double-sharp": 2,
        }
        octave += self.clef_octaves.get(self.cur_staffs[voice], 0)
        # minus clef-octave-change value
        acc = note.findtext("accidental")  # should be the notated accidental
        alter = note.findtext("pitch/alter")  # pitch alteration (MIDI)
        if ntrec.tab:
            return self.tab_note(int(alter or "0"), ptc, octave, voice, ntrec)
        # implies self.tstep is true (options.t was given)
        elif is_tab and self.tstep:
            nt = ["__", "_", "", "^", "^^"][
                int(alter or "0") + 2
            ] + add_octave(ptc, octave)
            info(
                "no string notation found for note %s in voice %d"
                % (nt, voice),
                True,
            )
        p = add_octave(ptc, octave)
        if alter is None:
            if acc is None:
                return p  # no acc, no alt
            if self.msralts.get(ptc, 0):
                alt = 0  # no alt but key implies alt -> natural!!
            if (p, voice) in self.cur_alts:
                alt = 0  # no alt but previous note had one -> natural!!
        elif acc is not None:
            alt = acc2alt[acc]  # acc takes precedence over the pitch here!
        else:  # now see if we really must add an accidental
            alt = int(float(alter))
            if (p, voice) in self.cur_alts:
                # the note in this voice has been altered before
                if alt == self.cur_alts[(p, voice)]:
                    return p  # alteration still the same
            elif alt == self.msralts.get(ptc, 0):
                return p  # alteration implied by the key
            tieElms = note.findall("tie") + note.findall("notations/tied")
            # in XML we have separate notated ties and playback ties
            if "stop" in [e.get("type") for e in tieElms]:
                return p  # don't alter tied notes
            info(
                "accidental %d added in part %d, measure %d, voice %d note %s"
                % (
                    alt,
                    self.measure.ixp + 1,
                    self.measure.ixm + 1,
                    voice + 1,
                    p,
                )
            )
        self.cur_alts[(p, voice)] = alt
        p = ["__", "_", "=", "^", "^^"][alt + 2] + p
        # and finally ... prepend the accidental
        return p

    def parse_note(self, n: E.Element):
        """parse a musicXML note tag"""
        note = Note()
        voice = int(n.findtext("voice", "1"))
        if self.is_sib:
            voice += 100 * int(
                n.findtext("staff", "1")
            )  # repair bug in Sibelius
        is_chord = n.find("chord") is not None
        p = n.findtext("pitch/step") or n.findtext("unpitched/display-step")
        o = n.findtext("pitch/octave") or n.findtext(
            "unpitched/display-octave"
        )
        r = n.find("rest")
        numer = n.findtext("time-modification/actual-notes")
        if numer:
            denom = n.findtext("time-modification/normal-notes", "-")
            note.fact = (int(numer), int(denom))
        note.tup = [x.get("type") for x in n.findall("notations/tuplet")]
        duration = n.findtext("duration")
        grace = n.find("grace")
        note.is_grace = grace is not None
        note.before, note.after = ([], "")
        # strings with ABC stuff that goes before or after a note/chord
        if grace is not None and not self.is_in_grace:  # open a grace sequence
            self.is_in_grace = True
            note.before = ["{"]
            if grace.get("slash") == "yes":
                note.before += ["/"]  # acciaccatura
        stop_grace = not note.is_grace and self.is_in_grace
        if stop_grace:  # close the grace sequence
            self.is_in_grace = False
            self.music.last_note.after += "}"  # close grace on lastenote.after
        if duration is None or note.is_grace:
            duration = 0
        if r is None and n.get("print-object") == "no":
            if is_chord:
                return
            r = 1  # turn invisible notes (that advance the time) into invisible rests
        note.duration = int(duration)
        if r is None and (not p or not o):  # not a rest and no pitch
            self.music.counter.increment(
                "nopt", voice
            )  # count unpitched notes
            o, p = 5, "E"  # make it an E5 ??
        is_tab = bool(self.cur_clefs) and self.cur_clefs.get(
            self.cur_staffs[voice], ""
        ).startswith("tab")
        notation = n.find("notations")  # add ornaments
        if notation is not None:
            self.do_notations(note, notation, is_tab)
        stem = (
            n.find("stem") if r is None else None
        )  # no !stemless! before rest
        if (
            stem is not None
            and stem.text == "none"
            and (not is_tab or voice in self.has_stems or self.tstep)
        ):
            note.before += ["s"]
            abc_out.stemless = True
        accidental = n.find("accidental")
        if accidental is not None and accidental.get("parentheses") == "yes":
            note.ntdec += "!courtesy!"
        if r is not None:
            noot = "x" if n.get("print-object") == "no" or is_tab else "z"
        else:
            noot = self.abc_notation(p, int(o), n, voice, note, is_tab)
        if n.find("unpitched") is not None:
            clef = self.cur_clefs[self.cur_staffs[voice]]
            # the current clef for this voice
            step = staff_step(p, int(o), clef, self.tstep)
            # (clef independent) step value of note on the staff
            instr = n.find("instrument")
            instr_id = instr.get("id") if instr is not None else "dummyId"
            midi = self.drum_instr.get(instr_id, abc_to_midi_pitch(noot))
            nh = n.findtext("notehead", "").replace(" ", "-")
            # replace spaces in XML notehead names for perc_map
            if nh == "x":
                noot = "^" + noot.replace("^", "").replace("_", "")
            if nh in ["circle-x", "diamond", "triangle"]:
                noot = "_" + noot.replace("^", "").replace("_", "")
            if nh and n.find("notehead").get("filled", "") == "yes":
                nh += "+"
            if nh and n.find("notehead").get("filled", "") == "no":
                nh += "-"
            self.drum_notes[(voice, noot)] = (step, midi, nh)
            # keep data for percussion map
        tieElms = n.findall("tie") + n.findall("notations/tied")
        # in XML we have separate notated ties and playback ties
        if "start" in [
            e.get("type") for e in tieElms
        ]:  # n can have stop and start tie
            noot = noot + "-"
        note.beam = sum(
            [1 for b in n.findall("beam") if b.text in ["continue", "end"]]
        ) + int(note.is_grace)
        lyrlast = 0
        rsib = re.compile(r"^.*verse")
        for e in n.findall("lyric"):
            lyrnum = int(
                rsib.sub("", e.get("number", "1"))
            )  # also do Sibelius numbers
            if lyrnum == 0:
                lyrnum = lyrlast + 1  # and correct Sibelius bugs
            else:
                lyrlast = lyrnum
            note.lyrics[lyrnum] = do_syllable(e)
        stem_dir = n.findtext("stem")
        if self.write_stems and stem_dir in ["up", "down"]:
            if stem_dir != self.stem_dirs.get(voice, ""):
                self.stem_dirs[voice] = stem_dir
                self.music.append_element(voice, f"[I:stemdir {stem_dir}]")
        if is_chord:
            self.music.add_chord(note, noot)
        else:
            xmlstaff = int(n.findtext("staff", "1"))
            if self.cur_staffs[voice] != xmlstaff:
                # the note should go to another staff
                dstaff = xmlstaff - self.cur_staffs[voice]
                # relative new staff number
                self.cur_staffs[voice] = xmlstaff
                # remember the new staff for this voice
                self.music.append_element(voice, "[I:staff %+d]" % dstaff)
                # insert a move before the note
            self.music.append_note(voice, note, noot)
        for slur in n.findall("notations/slur"):
            # self.music.last_note points to the last real note/chord inserted above
            slur.text
            self.match_slur(
                slur.get("type"),
                slur.get("number"),
                voice,
                self.music.last_note,
                note.is_grace,
                stop_grace,
            )  # match slur definitions

    def parse_attr(self, e: E.Element):
        """Parse a musicXML attribute tag."""
        signs = {
            "C1": "alto1",
            "C2": "alto2",
            "C3": "alto",
            "C4": "tenor",
            "F4": "bass",
            "F3": "bass3",
            "G2": "treble",
            "TAB": "tab",
            "percussion": "perc",
        }
        dvstxt = e.findtext("divisions")
        if dvstxt:
            self.measure.divs = int(dvstxt)
        steps = int(e.findtext("transpose/chromatic", "0"))
        # for transposing instrument
        fifths = e.findtext("key/fifths")
        first = self.music.time == 0 and self.measure.ixm == 0
        # first attributes in first measure
        if fifths:
            key, self.msralts = set_key(
                int(fifths), e.findtext("key/mode", "major")
            )
            if first and not steps and abc_out.key == "none":
                abc_out.key = key  # first measure -> header, if not transposing instrument or percussion part!
            elif key != abc_out.key or not first:
                self.measure.attr += f"[K:{key}]"  # otherwise -> voice
        beats = e.findtext("time/beats")
        if beats:
            unit = e.findtext("time/beat-type")
            meter = beats + "/" + unit
            if first:
                abc_out.meter = meter  # first measure -> header
            else:
                self.measure.attr += f"[M:{meter}]"  # otherwise -> voice
            self.measure.meter = int(beats), int(unit)
        self.measure.measure_duration = (
            self.measure.divs * self.measure.meter[0] * 4
        ) // self.measure.meter[1]
        # duration of measure in XML-divisions
        for measure_style in e.findall("measure-style"):
            n = int(measure_style.get("number", "1"))  # staff number
            voices = self.staff_map[n]  # all voices of staff n
            for measure_repeat in measure_style.findall("measure-repeat"):
                ty = measure_repeat.get("type")
                if ty == "start":
                    # remember start measure number and text voor each staff
                    self.repeat_str[n] = [
                        self.measure.ixm,
                        measure_repeat.text,
                    ]
                    for voice in voices:
                        # insert repeat into all voices, value will be overwritten at stop
                        self.music.insert_element(voice, self.repeat_str[n])
                elif (
                    ty == "stop"
                ):  # calculate repeat measure count for this staff n
                    start_ix, text_ = self.repeat_str[n]
                    repeat_count = self.measure.ixm - start_ix
                    if text_:
                        mid_str = f"{text_} "
                        repeat_count /= int(text_)
                    else:
                        mid_str = ""  # overwrite repeat with final string
                    self.repeat_str[n][
                        0
                    ] = f"[I:repeat {mid_str}{repeat_count}]"
                    del self.repeat_str[n]  # remove closed repeats
        toct = e.findtext("transpose/octave-change", "")
        if toct:
            steps += 12 * int(toct)  # extra transposition of toct octaves
        for clef in e.findall("clef"):  # a part can have multiple staves
            n = int(
                clef.get("number", "1")
            )  # local staff number for this clef
            sign = clef.findtext("sign")
            line = (
                clef.findtext("line", "")
                if sign not in ["percussion", "TAB"]
                else ""
            )
            cs = signs.get(sign + line, "")
            oct = clef.findtext("clef-octave-change") or "0"
            if oct:
                cs += {-2: "-15", -1: "-8", 1: "+8", 2: "+15"}.get(
                    int(oct), ""
                )
            self.clef_octaves[n] = -int(oct)
            # XML playback pitch -> ABC notation pitch
            if steps:
                cs += " transpose=" + str(steps)
            staff_details = e.find("staff-details")
            if staff_details and int(staff_details.get("number", "1")) == n:
                lines = staff_details.findtext("staff-lines")
                if lines:
                    lns = "|||" if lines == "3" and sign == "TAB" else lines
                    cs += f" staff_lines={lns}"
                    self.staff_lines = int(lines)  # remember for tab staves
                strings = staff_details.findall("staff-tuning")
                if strings:
                    tuning = [
                        st.findtext("tuning-step")
                        + st.findtext("tuning-octave")
                        for st in strings
                    ]
                    cs += f" strings={','.join(tuning)}"
                capo = staff_details.findtext("capo")
                if capo:
                    cs += f" capo={capo}"
            self.cur_clefs[n] = cs  # keep track of current clef (for perc_map)
            if first:
                self.clef_map[n] = cs
                # clef goes to header (where it is mapped to voices)
            else:
                voices = self.staff_map[
                    n
                ]  # clef change to all voices of staff n
                for voice in voices:
                    if (
                        n != self.cur_staffs[voice]
                    ):  # voice is not at its home staff n
                        dstaff = n - self.cur_staffs[voice]
                        self.cur_staffs[voice] = n
                        # reset current staff at start of measure to home position
                        self.music.append_element(voice, f"[I:staff {dstaff}]")
                    self.music.append_element(voice, f"[K:{cs}]")

    def find_voice(self, i: int, es: list[E.Element]):
        staff_num = int(
            es[i].findtext("staff", 1)
        )  # directions belong to a staff
        voices = self.staff_map[staff_num]  # voices in this staff
        v1 = voices[0] if voices else 1  # directions to first voice of staff
        if self.dirtov1:
            return staff_num, v1, v1  # option --v1
        for e in es[i + 1 :]:  # or to the voice of the next note
            if e.tag == "note":
                voice = int(e.findtext("voice", "1"))
                if self.is_sib:
                    voice += 100 * int(e.findtext("staff", "1"))
                    # repair bug in Sibelius
                stf = self.voice2staff[voice]  # use our own staff allocation
                return (
                    stf,
                    voice,
                    v1,
                )  # voice of next note, first voice of staff
            if e.tag == "backup":
                break
        return staff_num, v1, v1  # no note found, fall back to v1

    def do_direction(self, e: E.Element, i: int, es: list[E.Element]):
        """parse a musicXML direction tag"""

        def add_direction(x, v: int, time, staff_num: int):
            if not x:
                return
            vs = self.staff_map[staff_num] if "!8v" in x else [v]
            # ottava's go to all voices of staff
            for voice in vs:
                if time is not None:  # insert at time of encounter
                    self.music.append_element_at_time(
                        voice,
                        x.replace("(", ")").replace("ped", "ped-up"),
                        time,
                    )
                else:
                    self.music.append_element(voice, x)

        def start_stop(dtype: str, v: int, staff_num=1):
            typmap = {
                "down": "!8va(!",
                "up": "!8vb(!",
                "crescendo": "!<(!",
                "diminuendo": "!>(!",
                "start": "!ped!",
            }
            type = t.get("type", "")
            k = dtype + t.get("number", "1")
            # key to match the closing direction
            if type in typmap:  # opening the direction
                x = typmap[type]
                if k in self.dirStk:  # closing direction already encountered
                    stype, time = self.dirStk[k]
                    del self.dirStk[k]
                    if stype == "stop":
                        add_direction(x, v, time, staff_num)
                    else:
                        info(
                            "%s direction %s has no stop in part %d, measure %d, voice %d"
                            % (
                                dtype,
                                stype,
                                self.measure.ixp + 1,
                                self.measure.ixm + 1,
                                v + 1,
                            )
                        )
                        self.dirStk[k] = (type, v)
                        # remember voice and type for closing
                else:
                    self.dirStk[k] = (type, v)
                    # remember voice and type for closing
            elif type == "stop":
                if k in self.dirStk:  # matching open direction found
                    type, vs = self.dirStk[k]
                    del self.dirStk[k]  # into the same voice
                    if type == "stop":
                        info(
                            "%s direction %s has double stop in part %d, measure %d, voice %d"
                            % (
                                dtype,
                                type,
                                self.measure.ixp + 1,
                                self.measure.ixm + 1,
                                vs + 1,
                            )
                        )
                        x = ""
                    else:
                        x = (
                            typmap[type]
                            .replace("(", ")")
                            .replace("ped", "ped-up")
                        )
                else:  # closing direction found before opening
                    self.dirStk[k] = ("stop", self.music.time)
                    x = ""  # delay code generation until opening found
            else:
                raise ValueError("wrong direction type")
            add_direction(x, v, None, staff_num)

        tempo, words_text = None, ""
        placement = e.get("placement")
        stf, vs, v1 = self.find_voice(i, es)
        jmp = ""  # for jump sound elements: dacapo, dalsegno and family
        jmps = [
            ("dacapo", "D.C."),
            ("dalsegno", "D.S."),
            ("tocoda", "dacoda"),
            ("fine", "fine"),
            ("coda", "O"),
            ("segno", "S"),
        ]
        t = e.find("sound")  # there are many possible attributes for sound
        if t is not None:
            minst = t.find("midi-instrument")
            if minst:
                prg = minst.findtext("midi-instrument/midi-program")
                chn = minst.findtext("midi-instrument/midi-channel")
                vids = [
                    voice
                    for voice, id in self.voice_instrument.items()
                    if id == minst.get("id")
                ]
                if vids:
                    vs = vids[0]
                    # direction for the indentified voice, not the staff
                if abc_out.vol_pan > 0:
                    parm, instr = (
                        ("program", str(int(prg) - 1))
                        if prg
                        else ("channel", chn)
                    )
                    if instr:
                        self.music.append_element(
                            vs, f"[I:MIDI= {parm} {instr}]"
                        )
            tempo = t.get("tempo")  # look for tempo attribute
            if tempo:
                tempo = "%.0f" % float(tempo)
                # hope it is a number and insert in voice 1
                tempo_units = (1, 4)  # always 1/4 for sound elements!
            for r, v in jmps:
                if t.get(r, ""):
                    jmp = v
                    break
        for dir_type in e.findall("direction-type"):
            units: dict[str, Tuple[int, int]] = {
                "whole": (1, 1),
                "half": (1, 2),
                "quarter": (1, 4),
                "eighth": (1, 8),
            }
            metr = dir_type.find("metronome")
            if metr is not None:
                t = metr.findtext("beat-unit", "")
                if t in units:
                    tempo_units = units[t]
                else:
                    tempo_units = units["quarter"]
                if metr.find("beat-unit-dot") is not None:
                    tempo_units = simplify(
                        tempo_units[0] * 3, tempo_units[1] * 2
                    )
                tmpro = re.search(
                    r"\d[.\d+]", metr.findtext("per-minute", "-")
                )
                # look for a number
                if tmpro:
                    tempo = tmpro.group()
                    # overwrites the value set by the sound element of this direction
            t = dir_type.find("wedge")
            if t is not None:
                start_stop("wedge", vs)
            all_words = dir_type.findall("words")  # insert text annotations
            if not all_words:
                all_words = dir_type.findall("rehearsal")
                # treat rehearsal mark as text annotation
            if jmp:
                # ignore the words when a jump sound element is present in this direction
                self.music.append_element(vs, f"!{jmp}!", True)  # to voice
            else:
                for words in all_words:
                    plc = placement == "below" and "_" or "^"
                    if float(words.get("default-y", "0")) < 0:
                        plc = "_"
                    if words.text:
                        words_text += words.text.replace('"', r"\"").replace(
                            "\n", r"\n"
                        )
            words_text = words_text.strip()
            for key, val in dynamics_map.items():
                if dir_type.find("dynamics/" + key) is not None:
                    self.music.append_element(vs, val, True)  # to voice
            if dir_type.find("coda") is not None:
                self.music.append_element(vs, "O", True)
            if dir_type.find("segno") is not None:
                self.music.append_element(vs, "S", True)
            t = dir_type.find("octave-shift")
            if t is not None:
                start_stop("octave-shift", vs, stf)
                # assume size == 8 for the time being
            t = dir_type.find("pedal")
            if t is not None and self.render_pedal_dirs:
                if not self.pedal_dir_voice:
                    self.pedal_dir_voice = vs
                start_stop("pedal", self.pedal_dir_voice)
            if dir_type.findtext("other-direction") == "diatonic fretting":
                self.diafret = True
        if tempo:
            tempo = "%.0f" % float(tempo)
            # hope it is a number and insert in voice 1
            if self.music.time == 0 and self.measure.ixm == 0:
                # first measure -> header
                abc_out.tempo = tempo
                abc_out.tempo_units = tempo_units
            else:
                self.music.append_element(
                    v1, f"[Q:{tempo_units[0]}/{tempo_units[1]}={tempo}]"
                )  # otherwise -> 1st voice
        if words_text:
            self.music.append_element(vs, f'"{plc}{words_text}"', True)
            # to voice, but after tempo

    def parse_harmony(self, e: E.Element, i: int, es: list[E.Element]):
        """Parse a MusicXML harmony tag."""
        _, vt, _ = self.find_voice(i, es)
        short = {
            "major": "",
            "minor": "m",
            "augmented": "+",
            "diminished": "dim",
            "dominant": "7",
            "half-diminished": "m7b5",
        }
        accmap = {
            "major": "maj",
            "dominant": "",
            "minor": "m",
            "diminished": "dim",
            "augmented": "+",
            "suspended": "sus",
        }
        modmap = {
            "second": "2",
            "fourth": "4",
            "seventh": "7",
            "sixth": "6",
            "ninth": "9",
            "11th": "11",
            "13th": "13",
        }
        altmap = {"1": "#", "0": "", "-1": "b"}
        root = e.findtext("root/root-step", "")
        alt = altmap.get(e.findtext("root/root-alter", "-"), "")
        sus = ""
        kind = e.findtext("kind", "")
        if kind in short:
            kind = short[kind]
        elif "-" in kind:  # XML chord names: <triad name>-<modification>
            triad, mod = kind.split("-")
            kind = accmap.get(triad, "") + modmap.get(mod, "")
            if kind.startswith("sus"):
                kind, sus = "", kind  # sus-suffix goes to the end
        elif kind == "none":
            kind = e.find("kind").get("text", "")
        degrees = e.findall("degree")
        for d in degrees:  # chord alterations
            kind += altmap.get(
                d.findtext("degree-alter", "-"), ""
            ) + d.findtext("degree-value", "")
        kind = (
            kind.replace("79", "9").replace("713", "13").replace("maj6", "6")
        )
        bass = e.findtext("bass/bass-step", "") + altmap.get(
            e.findtext("bass/bass-alter", "-"), ""
        )
        self.music.append_element(
            vt,
            '"%s%s%s%s%s"' % (root, alt, kind, sus, bass and "/" + bass),
            True,
        )

    def do_barline(self, e: E.Element):
        """0 = no repeat, 1 = begin repeat, 2 = end repeat"""
        rep = e.find("repeat")
        if rep is not None:
            rep = rep.get("direction")
        if self.unfold:  # unfold repeat, don't translate barlines
            return rep and (rep == "forward" and 1 or 2) or 0
        loc = e.get("location", "right")  # right is the default
        if loc == "right":  # only change style for the right side
            style = e.findtext("bar-style")
            if style == "light-light":
                self.measure.rline = "||"
            elif style == "light-heavy":
                self.measure.rline = "|]"
        if rep is not None:  # repeat found
            if rep == "forward":
                self.measure.lline = ":"
            else:
                self.measure.rline = ":|"  # override barline style
        end = e.find("ending")
        if end is not None:
            if end.get("type") == "start":
                n = end.get("number", "1").replace(".", "").replace(" ", "")
                try:
                    list(map(int, n.split(",")))
                    # should be a list of integers
                except ValueError:
                    n = '"%s"' % n.strip()  # illegal musicXML
                self.measure.lnum = n
                # assume a start is always at the beginning of a measure
            elif self.measure.rline == "|":
                # stop and discontinue the same  in ABC ?
                self.measure.rline = "||"
                # to stop on a normal barline use || in ABC ?
        return 0

    def do_print(self, e):
        """print element, measure number -> insert a line break"""
        if e.get("new-system") == "yes" or e.get("new-page") == "yes":
            if not self.nolbrk:
                return "$"  # a line break

    def do_part_list(self, e):
        """Translate the start/stop-event-based XML-partlist into proper tree."""
        for score_part in e.findall("part-list/score-part"):
            midi = {}
            for m in score_part.findall("midi-instrument"):
                x = [
                    m.findtext(p, self.midi_defaults[i])
                    for i, p in enumerate(
                        ["midi-channel", "midi-program", "volume", "pan"]
                    )
                ]
                pan = float(x[3])
                if pan >= -90 and pan <= 90:
                    # would be better to map behind-pannings
                    pan = (float(x[3]) + 90) / 180 * 127
                    # XML between -90 and +90
                midi[m.get("id")] = [
                    int(x[0]),
                    int(x[1]),
                    float(x[2]) * 1.27,
                    pan,
                ]  # volume 100 -> MIDI 127
                up = m.findtext("midi-unpitched")
                if up:
                    self.drum_instr[m.get("id")] = int(up) - 1
                    # store MIDI-pitch for channel 10 notes
            self.instr_midis.append(midi)
        ps = e.find("part-list")  # partlist  = [groupelem]
        xs = get_part_list(ps)  # groupelem = partname | grouplist
        partlist, _ = parse_parts(xs, {}, [])
        # grouplist = [groupelem, ..., groupdata]
        return partlist  # groupdata = [group-symbol, group-barline, group-name, group-abbrev]

    def make_title(self, element_tree: E.ElementTree):
        def lines(text: str):
            return (line.strip() for line in text.splitlines())

        work_titles = list(lines(element_tree.findtext("work/work-title", "")))
        movement_titles = list(
            lines(element_tree.findtext("movement-title", ""))
        )
        composers, lyricists, credits = [], [], []
        for creator in element_tree.findall("identification/creator"):
            if creator.text:
                if creator.get("type") == "composer":
                    composers.extend(lines(creator.text))
                elif creator.get("type") in {"lyricist", "transcriber"}:
                    lyricists.extend(lines(creator.text))
        for rights in element_tree.findall("identification/rights"):
            if rights.text:
                lyricists.extend(lines(rights.text))
        for credit in element_tree.findall("credit"):
            cs = "".join(e.text or "" for e in credit.findall("credit-words"))
            credits.append(re.sub(r"\s*[\r\n]\s*", " ", cs))
        credit_strs = []
        for x in credits:  # skip redundant credit lines
            skip = False
            if self.ctf < 6 and (x in work_titles or x in movement_titles):
                skip = True  # sure skip
            if self.ctf < 5 and (x in composers or x in lyricists):
                skip = True  # almost sure skip
            if self.ctf < 4:
                # may skip too much
                for title in work_titles + movement_titles:
                    if title in x:
                        skip = True
                        break
            if self.ctf < 3:
                # skips too much
                for c in composers + lyricists:
                    if c in x:
                        skip = True
                        break
            if self.ctf < 2 and re.match(r"^[\d\W]*$", x):
                skip = True  # line only contains numbers and punctuation
            if not skip:
                credit_strs.append(x)
        if self.ctf == 0 and (work_titles or movement_titles):
            credit_strs = []  # default: only credit when no title set
        title_lines = []
        for work_title in work_titles:
            title_creditslines.append("T:" + work_title)
        for movement_title in movement_titles:
            if movement_title not in work_titles:
                title_lines.append("T:" + movement_title)
        for credit_str in credit_strs:
            title_lines.append("T:" + credit_str)
        for composer in composers:
            title_lines.append("C:" + composer)
        for lyricist in lyricists:
            title_lines.append("Z:" + lyricist)
        if title_lines:
            abc_out.title = "\n".join(title_lines)
        self.is_sib = "Sibelius" in (
            element_tree.findtext("identification/encoding/software") or ""
        )
        if self.is_sib:
            info("Sibelius MusicXML is unreliable")

    def do_defaults(self, element_tree: E.ElementTree):
        if not self.format_page:
            return  # return if -pf option absent
        defaults = element_tree.find("defaults")
        if defaults is None:
            return
        mils = defaults.findtext("scaling/millimeters")
        # mills == staff height (mm)
        tenths = defaults.findtext("scaling/tenths")  # staff height in tenths
        if not mils or not tenths:
            return
        xml_scale = float(mils) / float(tenths) / 10  # tenths -> mm
        space = 10 * xml_scale  # space between staff lines == 10 tenths
        abcScale = space / 0.2117
        # 0.2117 cm = 6pt = space between staff lines for scale = 1.0 in abcm2ps
        abc_out.pageFmt["scale"] = abcScale
        eks = 2 * ["page-layout/"] + 4 * ["page-layout/page-margins/"]
        eks = [
            a + b
            for a, b in zip(
                eks,
                "page-height,page-width,left-margin,right-margin,top-margin,bottom-margin".split(
                    ","
                ),
            )
        ]
        for i in range(6):
            v = defaults.findtext(eks[i])
            k = abc_out.pagekeys[
                i + 1
            ]  # pagekeys [0] == scale already done, skip it
            if not abc_out.pageFmt[k] and v:
                try:
                    abc_out.pageFmt[k] = float(v) * xml_scale  # -> cm
                except:
                    info("illegal value %s for XML element %s" % (v, eks[i]))
                    continue  # just skip illegal values

    def loc_staff_map(self, part, measures):
        """Map voice to staff with majority voting."""
        vmap = (
            {}
        )  # {voice -> {staff -> n}} count occurrences of voice in staff
        self.voice_instrument = {}  # {voice -> instrument id} for this part
        self.music.voice_nums = set()  # voice id's
        self.has_stems = {}
        # XML voice nums with at least one note with a stem (for tab key)
        self.staff_map, self.clef_map = (
            {},
            {},
        )  # staff -> [voices], staff -> clef
        notes = part.findall("measure/note")
        for n in notes:  # count staff allocations for all notes
            v = int(n.findtext("voice", "1"))
            if self.is_sib:
                v += 100 * int(
                    n.findtext("staff", "1")
                )  # repair bug in Sibelius
            self.music.voice_nums.add(
                v
            )  # collect all used voice id's in this part
            sn = int(n.findtext("staff", "1"))
            self.staff_map[sn] = []
            if v not in vmap:
                vmap[v] = {sn: 1}
            else:
                d = vmap[v]  # counter for voice v
                d[sn] = (
                    d.get(sn, 0) + 1
                )  # ++ number of allocations for staff sn
            x = n.find("instrument")
            if x is not None:
                self.voice_instrument[v] = x.get("id")
            x, noRest = n.findtext("stem"), n.find("rest") is None
            if noRest and (not x or x != "none"):
                self.has_stems[v] = 1  # XML voice v has at least one stem
        vks = list(vmap.keys())
        if self.javascript or self.is_sib:
            vks.sort()
        for v in vks:  # choose staff with most allocations for each voice
            xs = [(n, sn) for sn, n in vmap[v].items()]
            xs.sort()
            stf = xs[-1][1]  # the winner: staff with most notes of voice v
            self.staff_map[stf].append(v)
            self.voice2staff[v] = stf  # reverse map
            self.cur_staffs[v] = stf  # current staff of XML voice v

    def add_staff_map(self, xml2abcmap):
        """xml2abcmap: XML voice number -> global ABC voice number"""
        part = []  # default: brace on staffs of one part
        for stf, voices in sorted(self.staff_map.items()):
            # self.staff_map has XML staff and voice numbers
            locmap = [xml2abcmap[iv] for iv in voices if iv in xml2abcmap]
            nostem = [
                (iv not in self.has_stems) for iv in voices if iv in xml2abcmap
            ]
            # same order as locmap
            if locmap:  # ABC voice number of staff stf
                part.append(locmap)
                clef = self.clef_map.get(
                    stf, "treble"
                )  # {XML staff number -> clef}
                for i, iv in enumerate(locmap):
                    clef_attr = ""
                    if clef.startswith("tab"):
                        if nostem[i] and "nostems" not in clef:
                            clef_attr = " nostems"
                        if self.diafret and "diafret" not in clef:
                            clef_attr += (
                                " diafret"  # for all voices in the part
                            )
                    abc_out.clefs[iv] = clef + clef_attr
                    # add nostems when all notes of voice had no stem
        self.g_staff_map.append(part)

    def add_midi_map(self, ip, xml2abcmap):
        """Map ABC voices to MIDI settings."""
        instr = self.instr_midis[ip]  # get the MIDI settings for this part
        if instr.values():
            defInstr = list(instr.values())[
                0
            ]  # default settings = first instrument
        else:
            defInstr = self.midi_defaults  # no instruments defined
        xs = []
        for v, vabc in xml2abcmap.items():  # XML voice num, ABC voice num
            ks = sorted(self.drum_notes.items())
            ds = [
                (nt, step, midi, head)
                for (vd, nt), (step, midi, head) in ks
                if v == vd
            ]  # map perc notes
            id = self.voice_instrument.get(v, "")
            # get the instrument-id for part with multiple instruments
            if id in instr:  # id is defined as midi-instrument in part-list
                xs.append((vabc, instr[id] + ds))  # get MIDI settings for id
            else:
                xs.append(
                    (vabc, defInstr + ds)
                )  # only one instrument for this part
        xs.sort()  # put ABC voices in order
        self.midi_map.extend([midi for v, midi in xs])
        snaarmap = ["E", "G", "B", "d", "f", "a", "c'", "e'"]
        diamap = "0,1-,1,1+,2,3,3,4,4,5,6,6+,7,8-,8,8+,9,10,10,11,11,12,13,13+,14".split(
            ","
        )
        for k in sorted(self.tab_map.keys()):  # add %%map's for all tab voices
            v, noot = k
            string, fret = self.tab_map[k]
            if self.diafret:
                fret = diamap[int(fret)]
            vabc = xml2abcmap[v]
            string = self.staff_lines - int(string)
            xs = self.tab_voice_map.get(vabc, [])
            xs.append(
                "%%%%map tab%d %s print=%s heads=head%s\n"
                % (vabc, noot, snaarmap[string], fret)
            )
            self.tab_voice_map[vabc] = xs
            self.heads[fret] = 1  # collect noteheads for SVG defs

    def parse(self, fobj):
        vvmapAll = {}  # collect XML->ABC voice maps (xml2abcmap) of all parts
        e = E.parse(fobj)
        self.make_title(e)
        self.do_defaults(e)
        partlist = self.do_part_list(e)
        parts = e.findall("part")
        for ip, p in enumerate(parts):
            measures = p.findall("measure")
            self.loc_staff_map(p, measures)
            """{voice -> staff} for this part"""
            self.drum_notes = {}
            """(XML voice, ABC note) -> (MIDI note, note head)"""
            self.clef_octaves = {}
            """XML staff number -> current clef-octave-change"""
            self.cur_clefs = {}
            """XML staff number -> current ABC clef"""
            self.stem_dirs = {}
            """XML voice number -> current stem direction"""
            self.tab_map = {}
            """(XML voice, ABC note) -> (string, fret)"""
            self.diafret = False
            """use diatonic fretting"""
            self.staff_lines = 5
            self.music.init_voices(True)
            """create all voices"""
            repeat_count = 0
            """keep track of number of repetitions"""
            repeat_measure = 0
            """target measure of the repetition"""
            divisions = []
            """current value of <divisions> for each measure"""
            self.measure = Measure(ip)
            """various measure data"""
            while self.measure.ixm < len(measures):
                measure = measures[self.measure.ixm]
                repeat, line_break = 0, ""
                self.measure.reset()
                self.cur_alts = {}
                # passing accidentals are reset each measure
                es = list(measure)
                for i, e in enumerate(es):
                    if e.tag == "note":
                        self.parse_note(e)
                    elif e.tag == "attributes":
                        self.parse_attr(e)
                    elif e.tag == "direction":
                        self.do_direction(e, i, es)
                    elif e.tag == "sound":
                        self.do_direction(measure, i, es)
                        # sound element directly in measure!
                    elif e.tag == "harmony":
                        self.parse_harmony(e, i, es)
                    elif e.tag == "barline":
                        repeat = self.do_barline(e)
                    elif e.tag == "backup":
                        dt = int(e.findtext("duration", ""))
                        if check_bug(dt, self.measure):
                            self.music.increment_time(-dt)
                    elif e.tag == "forward":
                        dt = int(e.findtext("duration", ""))
                        if check_bug(dt, self.measure):
                            self.music.increment_time(dt)
                    elif e.tag == "print":
                        line_break = self.do_print(e)
                self.music.add_bar(line_break, self.measure)
                divisions.append(self.measure.divs)
                if repeat == 1:
                    repeat_measure = self.measure.ixm
                    self.measure.ixm += 1
                elif repeat == 2:
                    if repeat_count < 1:  # jump
                        self.measure.ixm = repeat_measure
                        repeat_count += 1
                    else:
                        repeat_count = 0  # reset
                        self.measure.ixm += 1  # just continue
                else:
                    self.measure.ixm += 1  # on to the next measure
            for rv in self.repeat_str.values():
                # close hanging measure-repeats without stop
                rv[0] = f"[I:repeat {rv[1]} 1]"
            xml2abcmap = self.music.output_voices(divisions, ip, self.is_sib)
            self.add_staff_map(xml2abcmap)  # update global staff map
            self.add_midi_map(ip, xml2abcmap)
            vvmapAll.update(xml2abcmap)
        if vvmapAll:  # skip output if no part has any notes
            abc_out.make_header(
                self.g_staff_map,
                partlist,
                self.midi_map,
                self.tab_voice_map,
                self.heads,
            )
            abc_out.write_all()
        else:
            info("nothing written, %s has no notes ..." % abc_out.name)


# ----------------
# Main Program
# ----------------
if __name__ == "__main__":
    from optparse import OptionParser
    from glob import glob
    from zipfile import ZipFile

    ustr = "%prog [-h] [-u] [-m] [-c C] [-d D] [-n CPL] [-b BPL] [-o DIR] [-v V]\n"
    ustr += "[-x] [-p PFMT] [-t] [-s] [-i] [--v1] [--noped] [--stems] <file1> [<file2> ...]"
    parser = OptionParser(usage=ustr, version=str(VERSION))
    parser.add_option("-u", action="store_true", help="unfold simple repeats")
    parser.add_option(
        "-m",
        action="store",
        help="0 -> no %%MIDI, 1 -> minimal %%MIDI, 2-> all %%MIDI",
        default=0,
    )
    parser.add_option(
        "-c",
        action="store",
        type="int",
        help="set credit text filter to C",
        default=0,
        metavar="C",
    )
    parser.add_option(
        "-d",
        action="store",
        type="int",
        help="set L:1/D",
        default=0,
        metavar="D",
    )
    parser.add_option(
        "-n",
        action="store",
        type="int",
        help="CPL: max number of characters per line (default 100)",
        default=0,
        metavar="CPL",
    )
    parser.add_option(
        "-b",
        action="store",
        type="int",
        help="BPL: max number of bars per line",
        default=0,
        metavar="BPL",
    )
    parser.add_option(
        "-o",
        action="store",
        help="store ABC files in DIR",
        default="",
        metavar="DIR",
    )
    parser.add_option(
        "-v",
        action="store",
        type="int",
        help="set volta typesetting behaviour to V",
        default=0,
        metavar="V",
    )
    parser.add_option("-x", action="store_true", help="output no line breaks")
    parser.add_option(
        "-p",
        action="store",
        help="pageformat PFMT (cm) = scale, pageheight, pagewidth, leftmargin, rightmargin, topmargin, botmargin",
        default="",
        metavar="PFMT",
    )
    parser.add_option(
        "-j",
        action="store_true",
        help="switch for compatibility with javascript version",
    )
    parser.add_option(
        "-t",
        action="store_true",
        help="translate perc- and tab-staff to ABC code with %%map, %%voicemap",
    )
    parser.add_option(
        "-s",
        action="store_true",
        help="shift node heads 3 units left in a tab staff",
    )
    parser.add_option(
        "--v1",
        action="store_true",
        help="start-stop directions allways to first voice of staff",
    )
    parser.add_option(
        "--noped",
        action="store_false",
        help="skip all pedal directions",
        dest="ped",
        default=True,
    )
    parser.add_option(
        "--stems",
        action="store_true",
        help="translate stem directions",
        dest="stm",
        default=False,
    )
    parser.add_option(
        "-i", action="store_true", help="read XML file from standard input"
    )
    options, args = parser.parse_args()
    if options.n < 0:
        parser.error("only values >= 0")
    if options.b < 0:
        parser.error("only values >= 0")
    if options.d and options.d not in [2**n for n in range(10)]:
        parser.error(
            "D should be on of %s" % ",".join([str(2**n) for n in range(10)])
        )
    options.p = options.p and options.p.split(",") or []  # ==> [] | [string]
    if len(args) == 0 and not options.i:
        parser.error("no input file given")
    out_path = options.o
    if out_path:
        if not os.path.exists(out_path):
            os.mkdir(out_path)
        if not os.path.isdir(out_path):
            parser.error("%s is not a directory" % out_path)
    fnmext_list = []
    for i in args:
        fnmext_list += glob(i)
    if options.i:
        fnmext_list = ["stdin.xml"]
    if not fnmext_list:
        parser.error("none of the input files exist")
    for X, name in enumerate(fnmext_list):
        fnm, ext = os.path.splitext(name)
        if ext.lower() not in {".xml", ".mxl", ".musicxml"}:
            info(
                "skipped input file %s, it should have extension .xml or .mxl"
                % name
            )
            continue
        if os.path.isdir(name):
            info("skipped directory %self. Only files are accepted" % name)
            continue
        if name == "stdin.xml":
            fobj = sys.stdin
        elif ext.lower() == ".mxl":  # extract .XML file from .mxl file
            z = ZipFile(name)
            for n in z.namelist():
                # assume there is always an XML file in a mxl archive !!
                if (n[:4] != "META") and (n[-3:].lower() in {"xml"}):
                    fobj = z.open(n)
                    break  # assume only one MusicXML file per archive
        else:
            fobj = open(name, "rb")  # open regular XML file

        abc_out = ABCOutput(fnm + ".abc", out_path, X, options)
        # create global ABC output object
        parser = Parser(options)  # XML parser
        try:
            parser.parse(fobj)  # parse file fobj and write ABC to <fnm>.abc
        except Exception as e:
            etype, value, traceback = sys.exc_info()  # works in python 2 & 3
            # info("** %s occurred: %s in %s" % (etype, value, name), False)
            raise e
