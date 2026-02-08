// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "scrape_addresses") {
        // Perform scraping logic
        scrapeProperties()
            .then(addresses => {
                sendResponse({ addresses: addresses });
            })
            .catch(error => {
                console.error("Scraping failed:", error);
                sendResponse({ addresses: [] });
            });
        return true; // Keep the message channel open for async response
    }
});

async function scrapeProperties() {
    // Utility to delay execution
    const delay = ms => new Promise(res => setTimeout(res, ms));

    // Scroll to bottom to trigger lazy loading
    let previousHeight = 0;
    let currentHeight = document.body.scrollHeight;
    let attempts = 0;
    const maxAttempts = 5; // Prevent infinite loops if height doesn't change but content loads

    console.log("Starting scroll...");

    while (attempts < maxAttempts) {
        window.scrollTo(0, document.body.scrollHeight);
        await delay(1500); // Wait for content to load

        currentHeight = document.body.scrollHeight;

        // If height hasn't changed, maybe we are done or button needs to be clicked?
        if (currentHeight === previousHeight) {
            attempts++;
        } else {
            previousHeight = currentHeight;
            attempts = 0; // Reset attempts if we found more content
        }
    }

    console.log("Finished scrolling. scraping...");

    // --- REFINED SCRAPING STRATEGY (Fixing 'sq ft' issue) ---

    let rawAddresses = [];

    // 1. Selector-based (Most accurate if classes exist)
    // Redfin Favorites often uses these specific classes for the address line
    const preciseSelectors = [
        ".homeAddressV2",
        ".addressDisplay",
        "div[data-rf-test-id='abp-streetLine']", // often just street
        ".street-address",
        ".full-address"
    ];

    const parentSelectors = [
        ".homeCardDetails",
        ".bottomV2",
        ".table-row"
    ];

    // Attempt 1: Look for full address containers
    document.querySelectorAll(preciseSelectors.join(",")).forEach(el => {
        // Often Redfin splits Street and City/State. We need to check if this element has the full string.
        // If it's just "123 Easy St", we might miss the city.
        // But .homeAddressV2 usually has "123 Easy St, Mountain View, CA 94043"
        if (el.innerText && /\d{5}/.test(el.innerText)) {
            rawAddresses.push(el.innerText);
        }
    });

    // Attempt 2: Strict Regex on Title attributes (very clean usually)
    document.querySelectorAll('a[title]').forEach(el => {
        const title = el.getAttribute('title');
        // Must look like an address: Ends in ZIP, starts with Number, no "sq ft"
        if (title && /^\d+\s/.test(title) && title.includes(",") && /\d{5}$/.test(title) && !title.includes("sq ft")) {
            rawAddresses.push(title);
        }
    });

    // Attempt 3: Regex scan with "Anti-SqFt" guard
    // We matched "593 sq ft" because "593" matched \d+ and "sq ft" matched text.
    // We will enforce that the word after the number is NOT sq/ft/bed/bath.
    if (rawAddresses.length === 0) {
        console.log("Selectors failed. Using strict regex scan...");

        // Negative lookahead to ensure we don't match "123 sq ft"
        // \d+ \s+ (?!sq|ft|bed|bath)
        const strictRegex = /\b\d+\s+(?!sq|ft|bed|bath|ac|wb)(?:[A-Z0-9\.]+\s+){1,4}(?:Road|Rd|Street|St|Drive|Dr|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Court|Ct|Way|Circle|Cir|Place|Pl|Terrace|Ter|Parkway|Pkwy|Square|Sq|Trail|Trl|Highway|Hwy)[\w\s\.]*,\s*[\w\s\.]+,\s*[A-Z]{2}\s+\d{5}/gi;

        const elements = document.querySelectorAll('div, span, a');
        elements.forEach(el => {
            // Only distinct text nodes
            if (el.children.length === 0 && el.innerText) {
                const matches = el.innerText.match(strictRegex);
                if (matches) {
                    matches.forEach(m => rawAddresses.push(m));
                }
            }
        });
    }

    // Deduplicate
    let uniqueAddresses = [...new Set(rawAddresses)];

    // Clean up function
    uniqueAddresses = uniqueAddresses.map(addr => {
        // Remove newlines
        let clean = addr.replace(/\n/g, ", ").trim();
        // Remove any leading junk if regex slipped (e.g. "593 sq ft, 123 Main")
        // Split by comma. If first part contains "sq ft", drop it?
        // Better: if it starts with "sq ft" or matches the bad pattern
        if (clean.match(/^\d+\s+sq\s*ft/i)) {
            return null;
        }
        return clean;
    }).filter(a => a !== null);

    // Re-filter for standard address shape
    uniqueAddresses = uniqueAddresses.filter(addr => /\d{5}/.test(addr)); // Must have zip

    // LIMIT TO 20
    const limitedAddresses = uniqueAddresses.slice(0, 20);
    console.log(`Final list: ${limitedAddresses.length} addresses.`);

    return limitedAddresses;
}
