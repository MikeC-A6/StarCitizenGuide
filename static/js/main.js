// Load marked.js for markdown parsing
const script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
document.head.appendChild(script);

document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('queryForm');
    const queryInput = document.getElementById('queryInput');
    const responseArea = document.getElementById('responseArea');
    const responseContent = document.getElementById('responseContent');
    const sourcesList = document.getElementById('sourcesList');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    // Configure marked options for better formatting
    script.onload = () => {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });
    };

    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = queryInput.value.trim();
        if (!query) {
            showError('Please enter a query');
            return;
        }

        // Show loading state
        const submitButton = queryForm.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Processing...
        `;

        // Hide previous response and errors
        responseArea.classList.add('d-none');
        errorAlert.classList.add('d-none');

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();

            if (data.success) {
                // Parse markdown and render response
                responseContent.innerHTML = marked.parse(data.response);
                
                // Update sources list
                sourcesList.innerHTML = data.sources
                    .map(source => `
                        <li class="mb-2">
                            <a href="${source}" target="_blank" rel="noopener noreferrer">
                                <i class="bi bi-box-arrow-up-right me-1"></i>
                                ${source}
                            </a>
                        </li>
                    `)
                    .join('');

                responseArea.classList.remove('d-none');
                
                // Smooth scroll to response
                responseArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                showError(data.error || 'Failed to process query');
            }
        } catch (error) {
            showError('An error occurred while processing your request');
            console.error('Error:', error);
        } finally {
            // Restore button state
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
        }
    });

    function showError(message) {
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});
