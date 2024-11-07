async function submitCode() {
    const form = document.getElementById('code-analysis-form');
    const formData = new FormData(form);

    try {
        // Send the form data to the backend for processing
        const response = await fetch('/analyze-code/', {
            method: 'POST',
            body: formData,
        });

        // Convert the response to JSON format
        const result = await response.json();

        // Call the function to display the results below the form
        displayResults(result);
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('results').innerHTML = `<p style="color: red;">An error occurred while analyzing the code. Please try again.</p>`;
    }
}

function displayResults(data) {
    // Display the analysis results in the "results" div
    document.getElementById('results').innerHTML = `
        <h3>Code Analysis Results:</h3>
        <p><strong>Accuracy:</strong> ${data.accuracy}</p>
        <p><strong>Optimization:</strong> ${data.optimization}</p>
        <p><strong>Suggestions:</strong> ${data.suggestions}</p>
    `;
}
