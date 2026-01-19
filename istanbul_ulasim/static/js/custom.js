document.addEventListener('DOMContentLoaded', function() {
    initCustomSelects();
});

function initCustomSelects() {
    // Only target standard selects, ignore if they have specific exclusion class
    const selects = document.querySelectorAll('select:not(.custom-select-native):not(.no-custom)');
    
    selects.forEach(select => {
        if (select.closest('.custom-select-wrapper')) return; // Already processed
        
        // Hide native select
        select.classList.add('custom-select-native');
        
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select-wrapper';
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);
        
        // Create trigger
        const trigger = document.createElement('div');
        trigger.className = 'custom-select-trigger';
        
        // Initial selected text
        const selectedOption = select.options[select.selectedIndex];
        const selectedText = selectedOption ? selectedOption.textContent : 'Seçiniz';
        
        trigger.innerHTML = `<span>${selectedText}</span><div class="custom-select-arrow"></div>`;
        wrapper.appendChild(trigger);
        
        // Create options container
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'custom-options';
        
        // Populate options
        Array.from(select.options).forEach(option => {
            const customOption = document.createElement('div');
            customOption.className = 'custom-option';
            customOption.textContent = option.textContent;
            customOption.dataset.value = option.value;
            
            if (option.selected) {
                customOption.classList.add('selected');
            }
            
            customOption.addEventListener('click', function(e) {
                e.stopPropagation();
                
                // Update native select
                select.value = option.value;
                select.dispatchEvent(new Event('change'));
                
                // Update trigger text
                trigger.querySelector('span').textContent = option.textContent;
                
                // Update styling
                wrapper.querySelectorAll('.custom-option').forEach(opt => opt.classList.remove('selected'));
                customOption.classList.add('selected');
                
                // Close dropdown
                wrapper.classList.remove('open');
            });
            
            optionsContainer.appendChild(customOption);
        });
        
        wrapper.appendChild(optionsContainer);
        
        // Toggle dropdown
        trigger.addEventListener('click', function(e) {
            e.stopPropagation();
            // Close other dropdowns
            document.querySelectorAll('.custom-select-wrapper').forEach(w => {
                if (w !== wrapper) w.classList.remove('open');
            });
            wrapper.classList.toggle('open');
        });
    });
    
    // Close on click outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.custom-select-wrapper')) {
            document.querySelectorAll('.custom-select-wrapper').forEach(w => {
                w.classList.remove('open');
            });
        }
    });
}
