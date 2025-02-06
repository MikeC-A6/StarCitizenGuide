document.addEventListener('DOMContentLoaded', function() {
    const queryInput = document.getElementById('queryInput');
    const submitButton = document.getElementById('submitQuery');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const responseArea = document.getElementById('responseArea');
    const responseContent = document.getElementById('responseContent');
    const errorArea = document.getElementById('errorArea');
    const errorMessage = document.getElementById('errorMessage');
    const sourcesList = document.getElementById('sourcesList');

    submitButton.addEventListener('click', async function() {
        const query = queryInput.value.trim();
        
        if (!query) {
            showError('Please enter a query');
            return;
        }

        // Reset UI
        hideError();
        showLoading();
        responseArea.classList.add('d-none');

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();

            if (data.success) {
                // Display response
                responseContent.textContent = data.response;
                
                // Display sources
                sourcesList.innerHTML = '';
                data.sources.forEach(source => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.href = source;
                    a.textContent = source;
                    a.target = '_blank';
                    a.classList.add('text-info');
                    li.appendChild(a);
                    sourcesList.appendChild(li);
                });
                
                responseArea.classList.remove('d-none');
            } else {
                showError(data.error || 'An error occurred');
            }
        } catch (error) {
            showError('Failed to communicate with server');
            console.error('Error:', error);
        } finally {
            hideLoading();
        }
    });

    function showLoading() {
        loadingSpinner.classList.remove('d-none');
        submitButton.disabled = true;
    }

    function hideLoading() {
        loadingSpinner.classList.add('d-none');
        submitButton.disabled = false;
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorArea.classList.remove('d-none');
    }

    function hideError() {
        errorArea.classList.add('d-none');
    }
});
