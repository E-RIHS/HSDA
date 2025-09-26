const cordra = require('cordra');

exports.beforeSchemaValidation = beforeSchemaValidation;


async function beforeSchemaValidation(object, context) {
    // validate material terms
    if (object.materialTerms) {
        for (const id of object.materialTerms) {
            const concept = await cordra.get(id);
            if (!('queryTerms' in concept && concept.queryTerms.includes('materials'))) {
                throw new Error(`Material term ${id} is not a valid material term`);
            }
        }
    }

    return object;
}