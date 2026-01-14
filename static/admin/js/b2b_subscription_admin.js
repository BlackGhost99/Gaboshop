/**
 * Auto-remplissage des champs plan_name et monthly_fee
 * quand un plan B2B est sélectionné
 */
(function($) {
    'use strict';
    
    $(document).ready(function() {
        var planField = $('#id_plan');
        var planNameField = $('#id_plan_name');
        var monthlyFeeField = $('#id_monthly_fee');
        
        // Fonction pour mettre à jour les champs depuis le plan sélectionné
        function updatePlanFields() {
            var selectedOption = planField.find('option:selected');
            var optionText = selectedOption.text().trim();
            
            if (!optionText || optionText === '---------') {
                planNameField.val('');
                monthlyFeeField.val('0.00');
                return;
            }
            
            // Le format est "Nom du plan - Prix FCFA/mois" ou "Nom du plan - GRATUIT"
            var parts = optionText.split(' - ');
            var planName = parts[0].trim();
            
            planNameField.val(planName);
            
            // Essayer d'extraire le prix si présent
            if (parts.length > 1) {
                var priceText = parts[1].trim();
                
                // Si c'est "GRATUIT", le prix est 0
                if (priceText.toUpperCase() === 'GRATUIT') {
                    monthlyFeeField.val('0.00');
                } else {
                    // Chercher un nombre (avec ou sans virgules, avant "FCFA")
                    var priceMatch = priceText.match(/^([\d,]+\.?\d*)/);
                    if (priceMatch) {
                        var price = priceMatch[1].replace(/,/g, '');
                        monthlyFeeField.val(parseFloat(price).toFixed(2));
                    } else {
                        monthlyFeeField.val('0.00');
                    }
                }
            } else {
                // Pas de prix dans le texte, mettre 0
                monthlyFeeField.val('0.00');
            }
        }
        
        // Écouter les changements sur le champ plan
        if (planField.length) {
            planField.on('change', function() {
                updatePlanFields();
            });
            
            // Mettre à jour au chargement de la page si un plan est déjà sélectionné
            if (planField.val()) {
                updatePlanFields();
            }
        }
    });
})(django.jQuery);

