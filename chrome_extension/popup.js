document.getElementById('sync-btn').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = "Requesting data...";
  statusDiv.style.color = "#0056b3";

  // Get active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab || (!tab.url.includes("redfin.com") && !tab.url.includes("localhost"))) {
    // Ideally check if content script is injectable, but let's try anyway or warn.
    // statusDiv.textContent = "Please go to Redfin Favorites.";
    // console.log("Not a Redfin tab.");
  }

  // Send message to content script
  try {
    const response = await chrome.tabs.sendMessage(tab.id, { action: "scrape_addresses" });
    
    if (response && response.addresses && response.addresses.length > 0) {
      statusDiv.textContent = `Found ${response.addresses.length} addresses. Syncing...`;
      
      // Send to local API
      try {
        const apiResponse = await fetch('http://localhost:8000/add_addresses', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ addresses: response.addresses })
        });
        
        if (apiResponse.ok) {
          const result = await apiResponse.json();
          statusDiv.textContent = `Success! Synced ${response.addresses.length} homes.`;
          statusDiv.style.color = "green";
        } else {
          statusDiv.textContent = "API Error: " + apiResponse.statusText;
          statusDiv.style.color = "red";
        }
      } catch (err) {
        statusDiv.textContent = "Connection Error: Is server running?";
        statusDiv.style.color = "red";
        console.error(err);
      }
      
    } else {
      statusDiv.textContent = "No addresses found.";
      statusDiv.style.color = "orange";
    }
    
  } catch (error) {
    statusDiv.textContent = "Error: Refresh page and try again.";
    console.error(error);
  }
});
