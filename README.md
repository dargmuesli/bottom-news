# BotTom News

Send the [daily video](https://www.tagesschau.de/100s/arabisch/) "Tagesschau in 100 Sekunden auf Arabisch" (German news in 100 seconds in Arabic) to a WhatsApp group with refugees.

Why? Because [the ones I know](https://jonas-thelemann.de/portfolio/faq/#refugees) are - at the moment - not all able to understand complex German sentences and should still be informed about what is going on in Germany and the rest of our world.

Nevertheless it should be easy to switch to the [German version](https://www.tagesschau.de/100sekunden/) of the "Tagesschau in 100 Sekunden" or even the [English one](http://www.tagesschau.de/100s/englisch/).

## Installation

This project builds on top of [yowsup](https://github.com/tgalal/yowsup/) extension, an unofficial WhatsApp API written in Python. To install it follow these [installation instructions](https://github.com/tgalal/yowsup/#installation).

## Errors

It took me a long time to get yowsup running. There were several problems that did not only originate from yowsup itself. The following paragraphs describe the fixes I applied and offer a downloadable solution.

### FFVideo

For everybody who does not know, [here you can find FFVideo's source](https://bitbucket.org/zakhar/ffvideo/wiki/Home).

#### Description

At the time of development (Q3 2016) FFVideo's extremely outdated version `0.0.13` could not be installed on my Raspberry Pi 2B running Raspbian Jessie via `pip` without errors and warnings. Ignoring the warnings I found out that the source's string `r_frame_rate` was not supported any more. This could be related to _my_ installed versions of [FFmpeg](https://ffmpeg.org/) and its extensions, so you might not have this problem.

#### Fix

You can see my steps to the solution in [my comments under issue 1689](https://github.com/tgalal/yowsup/issues/1689#issuecomment-245154280) and a downloadable fix in [my GitHub repository Dargmuesli/FFVideo](https://bitbucket.org/Dargmuesli/ffvideo). Though, I do not guarantee endless availability.

If you want to fix it yourself replace all occurrences of the string `r_frame_rate` with `avg_frame_rate` in the source file `FFVideo.c` and install that.

### Yowsup

Yowsup gave me two main problems that were pretty hard to fix as I was completely new to Python.

#### Description (A)

This problem stands somehow in relation to FFVideo, but is definitly a problem within yowsup. It seems like [importlib's](https://docs.python.org/2/library/importlib.html) `import_module` does not like my fixed install of FFVideo (or something else). It complains that it can't be imported while a simple `import FFVideo` in the python command shell does work fine.

#### Fix (A)

The fix is admittedly dirty, but it works. Add `from ffvideo import VideoStream` to [yowsup/common/tools.py](https://github.com/tgalal/yowsup/blob/master/yowsup/common/tools.py) and change the `VideoTools` class to the following:

```python
class VideoTools:
    @staticmethod
    def getVideoProperties(videoFile):
        s = VideoStream(videoFile)
        return s.width, s.height, s.bitrate, s.duration

    @staticmethod
    def generatePreviewFromVideo(videoFile):
        fd, path = tempfile.mkstemp('.jpg')
        stream = VideoStream(videoFile)
        stream.get_frame_at_sec(0).image().save(path)
        preview = ImageTools.generatePreviewFromImage(path)
        os.remove(path)
        return preview
```

I simply removed this is both functions:

```python
    with FFVideoOptionalModule() as imp:
    VideoStream = imp("VideoStream")
```

#### Description (B)

The act of sending a video via yowsup is <abbr title="Q3 2016">currently</abbr> doomed to failure. Whoever tries gets the error:

```python
AttributeError: type object 'DownloadableMediaMessageProtocolEntity' has no attribute 'fromFilePath'
```

No wonder, that's because `DownloadableMediaMessageProtocolEntity` actually has no `attribute 'fromFilePath'` because it's not a `VideoDownloadableMediaMessageProtocolEntity` (note the "Video"). Who could've thought! I believe that is caused by the fact that - while yowsup is not really being discontinued - its pull requests haven't been merged for a long time <abbr title="Q3 2016">now</abbr>. The one that fixes this problem is [#1564](https://github.com/tgalal/yowsup/pull/1564) labeled "_Builder support for audio and video upload_". Nice.

#### Fix (B)

Either replace the corresponding original files in `/yowsup/layers/protocol_media/protocolentities/` with a copy of [the fixed audio file](https://raw.githubusercontent.com/tanquetav/yowsup/75f548f78867ccc08821309d1c796b378d4b299d/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_audio.py) and/or [the fixed video file](https://raw.githubusercontent.com/tanquetav/yowsup/75f548f78867ccc08821309d1c796b378d4b299d/yowsup/layers/protocol_media/protocolentities/message_media_downloadable_video.py) by @tanquetav or install [my GitHub repository Dargmuesli/yowsup-mediafix](https://github.com/Dargmuesli/yowsup-mediafix) the usual way.
