chrome.runtime.onInstalled.addListener(() => {
    console.log('PortalX installed');
    chrome.sidePanel
      .setPanelBehavior({ openPanelOnActionClick: true })
      .catch((error) => console.error(error));
}); 