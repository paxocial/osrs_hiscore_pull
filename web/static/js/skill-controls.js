(function() {
  'use strict';

  var TRANSITION_MS = 250;

  function initSkillControls() {
    var sortSelect = document.getElementById('skill-sort');
    var filterCheckbox = document.getElementById('skill-filter-gains');
    var grid = document.getElementById('skills-grid');
    if (!sortSelect || !grid) return;

    var cards = Array.from(grid.querySelectorAll('.skill-card'));
    var original = cards.slice();
    var sorting = false;

    function getPositions() {
      var map = new Map();
      cards.forEach(function(card) {
        map.set(card, card.getBoundingClientRect());
      });
      return map;
    }

    function animateSort(sorted) {
      if (sorting) return;
      sorting = true;

      // FLIP: First — record current positions
      var first = getPositions();

      // Reorder DOM
      sorted.forEach(function(card) { grid.appendChild(card); });

      // FLIP: Last — record new positions
      var last = getPositions();

      // FLIP: Invert — offset each card back to old position
      cards.forEach(function(card) {
        var f = first.get(card);
        var l = last.get(card);
        if (!f || !l) return;
        var dx = f.left - l.left;
        var dy = f.top - l.top;
        if (dx === 0 && dy === 0) return;
        card.style.transition = 'none';
        card.style.transform = 'translate(' + dx + 'px, ' + dy + 'px)';
      });

      // FLIP: Play — animate to final position
      requestAnimationFrame(function() {
        requestAnimationFrame(function() {
          cards.forEach(function(card) {
            card.style.transition = 'transform 350ms cubic-bezier(0.25, 0.46, 0.45, 0.94)';
            card.style.transform = '';
          });
          setTimeout(function() {
            cards.forEach(function(card) {
              card.style.transition = '';
            });
            sorting = false;
          }, 360);
        });
      });
    }

    function sortCards(mode) {
      var sorted = original.slice();
      switch (mode) {
        case 'name':
          sorted.sort(function(a, b) {
            return (a.dataset.name || '').localeCompare(b.dataset.name || '');
          });
          break;
        case 'level-desc':
          sorted.sort(function(a, b) { return (b.dataset.level|0) - (a.dataset.level|0); });
          break;
        case 'level-asc':
          sorted.sort(function(a, b) { return (a.dataset.level|0) - (b.dataset.level|0); });
          break;
        case 'xp-desc':
          sorted.sort(function(a, b) { return (b.dataset.xp|0) - (a.dataset.xp|0); });
          break;
        case 'xp-asc':
          sorted.sort(function(a, b) { return (a.dataset.xp|0) - (b.dataset.xp|0); });
          break;
        case 'gain-desc':
          sorted.sort(function(a, b) { return (b.dataset.gain|0) - (a.dataset.gain|0); });
          break;
        case 'gain-asc':
          sorted.sort(function(a, b) { return (a.dataset.gain|0) - (b.dataset.gain|0); });
          break;
      }
      animateSort(sorted);
    }

    function filterCards() {
      var onlyGains = filterCheckbox && filterCheckbox.checked;
      var toHide = [];
      var toShow = [];

      cards.forEach(function(card) {
        var shouldShow = !onlyGains || (parseInt(card.dataset.gain, 10) || 0) > 0;
        var isHidden = card.classList.contains('filtered-out');

        if (shouldShow && isHidden) {
          toShow.push(card);
        } else if (!shouldShow && !isHidden) {
          toHide.push(card);
        }
      });

      // Phase 1: fade out cards that need hiding
      toHide.forEach(function(card) {
        card.classList.add('filtering-out');
      });

      // After transition, set display:none and reflow grid
      setTimeout(function() {
        toHide.forEach(function(card) {
          card.classList.remove('filtering-out');
          card.classList.add('filtered-out');
        });

        // Phase 2: reveal cards that need showing
        toShow.forEach(function(card) {
          card.classList.remove('filtered-out');
          card.classList.add('filtering-in');
        });

        // Trigger reflow then animate in
        requestAnimationFrame(function() {
          requestAnimationFrame(function() {
            toShow.forEach(function(card) {
              card.classList.remove('filtering-in');
            });
          });
        });
      }, TRANSITION_MS);
    }

    sortSelect.addEventListener('change', function() { sortCards(this.value); });
    if (filterCheckbox) {
      filterCheckbox.addEventListener('change', filterCards);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSkillControls);
  } else {
    initSkillControls();
  }

  document.body.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target && e.detail.target.id === 'skills-grid') {
      setTimeout(initSkillControls, 10);
    }
  });
})();
