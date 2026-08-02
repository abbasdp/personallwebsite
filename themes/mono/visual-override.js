/*
 * Custom overrides for Abbas Davarpanah free-software site theme.
 * Merged into style.css by Publii on generate.
 */

var generateOverride = function (params) {
	let output = '';

	if (params.galleryZoom !== true) {
		output += `
		.pswp--zoom-allowed .pswp__img {
			cursor: default !important;
		}`;
	}

	if (params.lazyLoadEffect === 'fadein') {
		output += `
		img[loading] {
			opacity: 0;
		}

		img.is-loaded {
			opacity: 1;
			transition: opacity 0.7s cubic-bezier(0.215, 0.61, 0.355, 1), transform .5s ease-out;
		}`;
	}

	/* Libre micro-tweaks that depend on theme tokens */
	output += `
	/* Stronger accent links in entry content */
	.content__entry a {
		color: var(--accent-medium);
	}

	/* Sticky left bar breathing room for RTL libre layout */
	@media all and (min-width: 56.25em) {
		.left-bar__inner {
			padding-inline-end: 0.25rem;
		}
	}

	/* Softer page background pattern for free-software calm */
	.hero {
		background-size: 18px 18px;
		background-position: 0 0, 9px 9px;
	}
	`;

	return output;
};

module.exports = generateOverride;
