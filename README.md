![PlayThis](https://raw.githubusercontent.com/anxdpanic/plugin.video.playthis/master/icon.png)
#PlayThis

The PlayThis add-on will attempt to find and resolve<sup>1</sup> media from a url to play or open. A history list is available for future use, exporting to .m3u/.strm<sup>2</sup> and casting to a remote PlayThis add-on. Supports video, audio, images and executable<sup>3</sup>.
* <sup>1</sup> resolves using URLResolver and youtube-dl
* <sup>2</sup> M3U only usable in Kodi w/ PlayThis installed
* <sup>3</sup> 'executable' items are urls with potential results available through scraping


- Installation
    -
    * Kodi 17+: Enable - `Settings -> System -> Add-ons -> Unknown Sources`
    1. Download repository: [repository.anxdpanic-x.x.x.zip](https://offshoregit.com/anxdpanic/repository/zips/repository.anxdpanic/repository.anxdpanic-0.9.3.zip) (also available on [Fusion](https://www.tvaddons.ag/fusion-installer-kodi/))
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

    _**Firefox 47+ Context Menu**_

    - Download extension from [AMO Gallery](https://addons.mozilla.org/en-US/firefox/addon/playthis/)
    - GitHub: [PlayThis \(Firefox\)](https://github.com/anxdpanic/PlayThis-Extension/tree/firefox#playthis-firefox)

- Support
    -

    Post an [Issue](https://github.com/anxdpanic/plugin.video.playthis/issues) , or visit [#the_projects on Snoonet](https://kiwiirc.com/client/irc.snoonet.org/The_Projects)

---

Special thanks to [@konsumer420](https://twitter.com/konsumer420) for the icons/artwork
