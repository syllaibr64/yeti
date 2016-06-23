$(function () {
  $('.markdown').each(function (index) {
    var input = $(this);
    var simplemde = new SimpleMDE({
      element: input[0],
      autosave: {
        enabled: true,
        uniqueId: window.location.href
      },
      renderingConfig: {
        codeSyntaxHighlighting: true
      },
      spellChecker: false
    });
    input.data('editor', simplemde);

    inlineAttachment.editors.codemirror4.attach(simplemde.codemirror, {
      uploadUrl: '/api/files/',
      extraHeaders: {
        Accept: 'application/json'
      }
    });
  });
});
