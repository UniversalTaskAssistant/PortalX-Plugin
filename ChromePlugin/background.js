chrome.runtime.onInstalled.addListener(() => {
    console.log('UTAWeb Assistant installed');
    chrome.sidePanel
      .setPanelBehavior({ openPanelOnActionClick: true })
      .catch((error) => console.error(error));
}); 