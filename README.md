![PlayThis](https://raw.githubusercontent.com/anxdpanic/PlayThis-Extension/chrome/images/icon_128.png)
#PlayThis

The PlayThis add-on will attempt to resolve a provided url with UrlResolver and start playback if possible.

- Requirements
    -
    - Kodi 14+

- Usage
    -
    _**Video Add-on**_

    Enter url in dialog, or choose from history

    _**example.strm**_
    ```
    plugin://plugin.video.playthis/?mode=play&player=false&path=http%3A%2F%2Fwww.dailymotion.com%2Fvideo%2Fx3ol7gj_incredible-freefall-skydiving-over-rio-de-janeiro_sport
    ```
    _**[userdata](http://kodi.wiki/view/userdata)/favorites.xml**_
    ```
    <favourites>
        <favourite name="Example ActivateWindow">ActivateWindow(10025,&quot;plugin://plugin.video.playthis/?mode=play&amp;player=true&amp;path=http%3A%2F%2Fwww.dailymotion.com%2Fvideo%2Fx3ol7gj_incredible-freefall-skydiving-over-rio-de-janeiro_sport&quot;,return)</favourite>
        <favourite name="Example PlayMedia">PlayMedia(&quot;plugin://plugin.video.playthis/?mode=play&amp;player=false&amp;path=http%3A%2F%2Fwww.dailymotion.com%2Fvideo%2Fx3ol7gj_incredible-freefall-skydiving-over-rio-de-janeiro_sport&quot;)</favourite>
    </favourites>
    ```

    _**Google Chrome Context Menu**_

    - Download extension: https://chrome.google.com/webstore/detail/playthis/adddkaonokkecefokdanjpaamfajogel
    - GitHub: https://github.com/anxdpanic/PlayThis-Extension/tree/chrome

    _**Firefox 47+ Context Menu**_

    - Download extension: https://addons.mozilla.org/en-US/firefox/addon/playthis/
    - GitHub: https://github.com/anxdpanic/PlayThis-Extension/tree/firefox

---

Special thanks to **@konsumer420** for the icons/artwork
