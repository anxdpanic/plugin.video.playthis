![PlayThis](icon.png)
# PlayThis

[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Factions-badge.atrox.dev%2Fanxdpanic%2Fplugin.video.playthis%2Fbadge&logo=none)](https://actions-badge.atrox.dev/anxdpanic/plugin.video.playthis/goto)
![License](https://img.shields.io/badge/license-GPL--3.0--only-success.svg)
![Kodi Version](https://img.shields.io/badge/kodi-jarvis%2B-success.svg)
![Contributors](https://img.shields.io/github/contributors/anxdpanic/plugin.video.playthis.svg)

The PlayThis add-on will attempt to find and resolve<sup>1</sup> media from a url to play or open. A history list is available for future use, exporting to .m3u/.strm<sup>2</sup> and sending to a remote PlayThis add-on. Supports video, audio, images and executable<sup>3</sup>.
* <sup>1</sup> resolves using ResolveURL(optional) or URLResolver(optional), and youtube-dl
* <sup>2</sup> M3U only usable in Kodi w/ PlayThis installed
* <sup>3</sup> 'executable' items are urls with potential results available through scraping


- Installation
    -
    * Kodi 17+: Enable - `Settings -> System -> Add-ons -> Unknown Sources`
    1. Download repository 
        - Kodi 16-18: [repository.anxdpanic-x.x.x.zip](https://panicked.xyz/repositories/repository.anxdpanic-2.0.0.zip)
        - Kodi 19: [repository.anxdpanic-x.x.x+matrix.1.zip](https://panicked.xyz/repositories/matrix/repository.anxdpanic-2.0.0+matrix.1.zip)
    2. [Install from zip file](http://kodi.wiki/view/Add-on_manager#How_to_install_from_a_ZIP_file) (repository.anxdpanic-x.x.x.zip)
    3. [Install from repository](http://kodi.wiki/view/add-on_manager#How_to_install_add-ons_from_a_repository) (anxdpanic Add-on Repository)

- Usage
    -

    Enter url in dialog, choose from history, send url from web browser, add to favorites from history/M3U, curate history list and export to M3U, or create/export a strm.  

    _**example.strm**_
    ```
    plugin://plugin.video.playthis/?mode=play&player=false&path=http%3A%2F%2Fwww.dailymotion.com%2Fvideo%2Fx3ol7gj_incredible-freefall-skydiving-over-rio-de-janeiro_sport
    ```

    _**Google Chrome Context Menu**_

    - Download extension from [Chrome Web Store](https://chrome.google.com/webstore/detail/playthis/adddkaonokkecefokdanjpaamfajogel)
    - GitHub: [PlayThis \(Google Chrome\)](https://github.com/anxdpanic/PlayThis-Extension/tree/chrome#playthis-google-chrome)

    _**Firefox 53+ Context Menu**_

    - Download extension from [AMO Gallery](https://addons.mozilla.org/en-US/firefox/addon/playthis/)
    - GitHub: [PlayThis \(Firefox\)](https://github.com/anxdpanic/PlayThis-Extension/tree/firefox#playthis-firefox)

- Support
    -

    Post an [Issue](https://github.com/anxdpanic/plugin.video.playthis/issues)
---

Special thanks to [@konsumer420](https://twitter.com/konsumer420) for the icons/artwork
