//////////////////////////////////////////////
// Logic when pushing Door Status
//////////////////////////////////////////////
async function waitWarn(a) {
    document.getElementById("Submit").disabled = true;
    //document.getElementById("Submit").style.backgroundColor = "orange";
    if (a === 0) {
        try {
            const response = await fetch('/api/run');
            
            if (response.ok) {
                console.log("Run control successful.");
            } else {
                throw new Error('Run command failed with status: ' + response.status);
            }
        } catch (error) {
            console.error('Run Error:', error);
            document.getElementById("warnLabel").textContent = "Error during RUN.";
        }
    } else if (a === 1) {
        updateStatus(false);
    }
    document.getElementById("Submit").disabled = false;
}
//document.addEventListener('DOMContentLoaded', updateStatus);
document.addEventListener('DOMContentLoaded', () => {
    const fullUIBtn = document.getElementById('fullUIBtn');
    fullUIBtn.addEventListener('click', function() {
        window.location.href = '/';
    });
});
