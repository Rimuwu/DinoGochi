<!-- ![[{{image}}.png]] -->

{{type}} {{rank}}

key - {{original_key}}
image - {{image}}

{{#if description}}
Description - {{description}}
{{/if}}

{{#if loc_create}}
{{#each loc_create}}
Create - [[{{this}}]]
{{/each}}
{{/if}}

{{#if recipes}}
{{#each recipes}}
recipe - [[{{this}}]]
{{/each}}
{{/if}}
