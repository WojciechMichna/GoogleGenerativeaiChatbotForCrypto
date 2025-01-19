// Make the bubble editable
function makeEditable(element) {
    element.setAttribute("contenteditable", "true");
    element.focus();

    // Optional: Make it non-editable when it loses focus
    element.addEventListener("blur", () => {
        element.removeAttribute("contenteditable");
    });
}

function removeBubbles(element) {
  current = element.parentNode
  while (current) {
    let next = current.nextSibling; // Store the next sibling before removal
    current.remove(); // Remove the current sibling
    current = next; // Move to the next sibling
  }
}


// Allow dropping files
function allowDrop(event) {
    event.preventDefault();
}

function uploadFile(file, bubble, img_element) {
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('File uploaded successfully');
            img_element.src = '/images/' + data.jpg_file;
        } else {
            console.error('File upload failed');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function handleRemoveButtonClick(event) {
  const container = event.target.closest('.image-container');
  if (container) {
    container.remove(); // Remove the entire container
  }
}

// Handle file drop
function handleDrop(event) {
    event.preventDefault();
    const files = event.dataTransfer.files;

    if (files.length > 0) {
        const file = files[0];
        const bubble = event.target;
        const bubbleParent = bubble.parentNode;

        // Remove previous file display (optional)
        /*
        const previousDisplay = bubbleParent.querySelector('.image-miniature, .file-icon');
        if (previousDisplay) {
            previousDisplay.remove();
        }
        */

        bubble.dataset.fileName = file.name; // Store the file name in a data attribute

        if (file.type.startsWith('image/')) {
            // Create an image element for the miniature
            const imageContainer = document.createElement('div');
            imageContainer.className = 'image-container';

            const img = document.createElement('img');
            img.className = 'image-miniature';
            img.src = URL.createObjectURL(file); // Generate a temporary URL for the image

            imageContainer.appendChild(img);

            const removeButton = document.createElement('button');
            removeButton.className = 'remove-button';
            removeButton.textContent = 'X';
            removeButton.addEventListener('click', handleRemoveButtonClick);

            imageContainer.appendChild(removeButton);
            bubbleParent.insertBefore(imageContainer, bubbleParent.firstChild);

            uploadFile(file, bubble, img);
        }
    }
}

// Collect data from all bubbles and send it
function sendData() {
    const bubbles = document.querySelectorAll('.bubble:not(.function_bubble)');
    const data = [];

    const overlay = document.getElementById('darkOverlay');
    overlay.style.display = 'flex';

    bubbles.forEach((bubble) => {
        const text = bubble.textContent.trim();
        const fileName = bubble.dataset.fileName || null;
        var files = [];
        bubble.parentElement.querySelectorAll('img').forEach((img) => {
          const fullPath = img.src; // Full URL
          const fileName = fullPath.split('/').pop(); // Extract the file name
          files.push(fileName);
        });

        data.push({
            type: bubble.classList.contains('blue') ? 'user' : 'model',
            text: text,
            files: files,
        });
    });

    const jsonData = JSON.stringify(data);
    // Send data to the server
    fetch('/send', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: jsonData,
    })
    .then(response => {
        overlay.style.display = 'none';
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(result => {
        console.log('Success:', result.response);
        const template = document.getElementById('my-template');

        // Step 2: Clone the template content
        const clone = template.content.cloneNode(true);

        // Step 3: Find the gray bubble inside the cloned template
        const grayBubble = clone.querySelector('.bubble.gray');

        // Step 4: Modify the text content of the gray bubble
        grayBubble.textContent = result.response;

        // Step 5: Append the modified content to the container with class 'bubble_container'
        const container = document.querySelector('.bubble_container');
        container.appendChild(clone);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function saveBubbleContainerContent() {
    // Find the div with class "bubble_container"
    const bubbleContainer = document.querySelector('.bubble_container');

    if (!bubbleContainer) {
        console.error('No element with class "bubble_container" found.');
        return;
    }

    // Extract the HTML content inside the div
    const htmlContent = bubbleContainer.innerHTML;

    // Create a JSON object
    const jsonData = {
        save: htmlContent
    };

    // Convert JSON object to a string
    const jsonString = JSON.stringify(jsonData, null, 2);

    // Create a Blob object from the JSON string
    const blob = new Blob([jsonString], { type: 'application/json' });

    // Create a temporary download link
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(blob);
    downloadLink.download = 'bubble_container.json'; // File name for the downloaded JSON

    // Trigger the download
    downloadLink.click();

    // Clean up the temporary link
    URL.revokeObjectURL(downloadLink.href);
}

function loadAndRestoreBubbleContainerFromJson(json) {
    try {
        const jsonData = JSON.parse(json); // Parse the JSON
        if (!jsonData.save) {
            console.error('Invalid JSON: Missing "save" property.');
            return;
        }

        const htmlContent = jsonData.save; // Extract the "save" property

        // Find or create a bubble_container div
        let bubbleContainer = document.querySelector('.bubble_container');
        if (!bubbleContainer) {
            bubbleContainer = document.createElement('div');
            bubbleContainer.className = 'bubble_container';
            document.body.appendChild(bubbleContainer); // Append to body if it doesn't exist
        }

        // Restore the HTML content
        bubbleContainer.innerHTML = htmlContent;

        console.log('HTML content restored successfully.');
    } catch (error) {
        console.error('Error parsing JSON file:', error);
    }
}

function loadAndRestoreBubbleContainer(event) {
    const file = event.target.files[0]; // Get the uploaded file

    if (!file) {
        console.error('No file selected.');
        return;
    }

    const reader = new FileReader();

    // Read the file content
    reader.onload = function(e) {
        loadAndRestoreBubbleContainerFromJson(e.target.result);
    };

    reader.readAsText(file); // Read the file as text
}

// Attach the file input to the button
document.getElementById('uploadButton').addEventListener('click', function() {
    // Programmatically trigger the hidden file input
    document.getElementById('fileInput').click();
});

// Attach the change event to the hidden file input
document.getElementById('fileInput').addEventListener('change', loadAndRestoreBubbleContainer);
