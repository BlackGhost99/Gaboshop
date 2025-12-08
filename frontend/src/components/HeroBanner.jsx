import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

/**
 * Hero Banner avec carrousel de promotions
 * Mobile-first design - Dynamique
 */
const HeroBanner = ({ promotions = [] }) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  // Default promotions si aucune donnée
  const defaultPromotions = [
    {
      id: 1,
      title: 'Offres du jour',
      subtitle: 'Jusqu\'à -50% sur une sélection',
      cta: 'Voir les offres',
      bg: 'bg-gradient-to-r from-cta-500 to-orange-400',
      icon: '🎉',
    },
    {
      id: 2,
      title: 'Livraison gratuite',
      subtitle: 'Dès 50 000 FCFA d\'achat',
      cta: 'Découvrir',
      bg: 'bg-gradient-to-r from-primary-600 to-blue-400',
      icon: '🚚',
    },
    {
      id: 3,
      title: 'Nouveautés',
      subtitle: 'Découvrez les derniers produits',
      cta: 'Explorer',
      bg: 'bg-gradient-to-r from-accent-500 to-green-400',
      icon: '✨',
    },
  ];

  // Utiliser les promotions reçues ou les defaults
  const slides = promotions && promotions.length > 0 ? promotions : defaultPromotions;

  // Auto-rotate carousel
  useEffect(() => {
    if (slides.length === 0) return;
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % slides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [slides.length]);

  return (
    <div className="relative w-full overflow-hidden">
      {/* Carousel */}
      <div className="relative h-64 md:h-96 flex items-center justify-center overflow-hidden">
        {slides.map((slide, index) => (
          <div
            key={slide.id}
            className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${
              index === currentSlide ? 'opacity-100' : 'opacity-0'
            } ${slide.bg || 'bg-gradient-to-r from-primary-600 to-primary-400'}`}
          >
            <div className="absolute inset-0 bg-black/20" />
            <div className="relative h-full flex flex-col items-center justify-center text-center px-6 py-8">
              <div className="text-5xl md:text-6xl mb-4">{slide.icon || '💼'}</div>
              <h2 className="text-2xl md:text-4xl font-bold text-white mb-2">
                {slide.title}
              </h2>
              <p className="text-base md:text-lg text-white/90 mb-6 max-w-lg">
                {slide.subtitle}
              </p>
              <Link
                to="/products"
                className="px-6 py-3 bg-white text-gray-900 font-semibold rounded-lg hover:bg-gray-100 transition-colors shadow-lg"
              >
                {slide.cta || 'Découvrir'}
              </Link>
            </div>
          </div>
        ))}

        {/* Navigation Dots */}
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 flex gap-2 z-10">
          {slides.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentSlide(index)}
              className={`w-3 h-3 rounded-full transition-all ${
                index === currentSlide
                  ? 'bg-white w-8'
                  : 'bg-white/50 hover:bg-white/75'
              }`}
              aria-label={`Slide ${index + 1}`}
            />
          ))}
        </div>

        {/* Previous Button */}
        <button
          onClick={() =>
            setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length)
          }
          className="absolute left-4 top-1/2 transform -translate-y-1/2 z-10 bg-white/20 hover:bg-white/40 text-white p-2 rounded-full transition-colors"
          aria-label="Previous slide"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>

        {/* Next Button */}
        <button
          onClick={() => setCurrentSlide((prev) => (prev + 1) % slides.length)}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 z-10 bg-white/20 hover:bg-white/40 text-white p-2 rounded-full transition-colors"
          aria-label="Next slide"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default HeroBanner;
