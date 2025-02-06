window.addEventListener("DOMContentLoaded", () => {
    console.log("Custom search script loaded.");

    // Debug search index loading
    const checkSearchIndex = setInterval(() => {
        console.log("Checking for search index...");
        console.log("window.search:", window.search);

        if (window.search) {
            console.log("Search object exists.");
            console.log("Search index:", window.search._index);

            if (window.search._index) {
                console.log("Search index found, enhancing functionality.");

                // Sanitize the search results to remove HTML tags
                const searchResults = document.querySelectorAll('.search-results .search');
                searchResults.forEach(result => {
                    result.innerHTML = result.innerHTML.replace(/<\/?[^>]+(>|$)/g, ""); // Remove HTML tags
                });

                // Clear the interval once done
                clearInterval(checkSearchIndex);
            }
        }
    }, 100);
});
