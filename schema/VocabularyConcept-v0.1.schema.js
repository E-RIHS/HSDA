const cordra = require('cordra');

exports.methods = {};
exports.methods.updateObjectWithNarrower = updateObjectWithNarrower;

async function updateObjectWithNarrower(object, context) {
    const query = 'type:VocabularyConcept AND /broader/_:"' + object.id + '"';
    const response = await cordra.search(query);

    const narrower = [];
    if ('results' in response) {
        for (const r of response.results) {
            narrower.push(r.id);
        }
    }
    
    object.content.narrower = narrower;
    return object;
}