'use strict';

// for debug purposes
var pr = console.log.bind(console);

var Synchronize = {

	RETRY: 1000,

	on: function(name, callback, context) {
		Backbone.Events.on.call(this, name, callback, context);

		if (name == 'sync' && !this._fetching) {
			this._fetch();
		}

		return this;
	},

	off: function(name, callback, context) {
		Backbone.Events.off.call(this, name, callback, context);

		if (!this._events['sync'] && this._fetching) {
			this._fetching.abort();
			this._fetching = null;
		}

		return this;
	},

	_fetch: function(options) {
		options = _.extend(options || {}, {
			'ifModified': true,
			'success': function(model, response, options) {
				if (options.xhr.status == 200) {
					model._fetch();
				} else {
					model._fetching = null;

					_.delay(_.bind(model._fetch, model), Synchronize.RETRY);
				}
			},
			'error': function(model, response, options) {
				_.delay(_.bind(model._fetch, model), Synchronize.RETRY);
			}
		});

		this._fetching = this.fetch(options);
	}
}

var Game = Backbone.Model.extend({
	urlRoot: '/games/',

	initialize: function(attributes, options) {
		this.players = new Players([], {
			'game': this
		});
	},
});

var Player = Backbone.Model.extend({

});
_.extend(Player.prototype, Synchronize);

var Players = Backbone.Collection.extend({
	model: Player,

	url: function() {
		return this.game.url() + '/players/';
	},

	comparator: function(player) {
		return -player.get('score');
	},

	initialize: function(models, options) {
		this.game = options.game;

		this.on('reset change', this.sort, this);
	},

	parse: function(response, options) {
		if (response) {
			return response.players;
		}
	}
});
_.extend(Players.prototype, Synchronize);

var ScoreBoard = Backbone.View.extend({
	template: _.template(
		'<li id="player_<%- player.id %>">' +
			'<div class="avatar"><img src="http://robohash.org/<%- player.name %>"></img></div>' +
			'<div class="position">-</div>' +
			'<div class="name"><%- player.name %></div>' +
			'<div class="moves"><%- player.moves %></div>' +
			'<div class="score"><%- player.score %></div>' +
		'</li>'
	),

	initialize: function() {

		var _this = this;
		var topHeight = 65;
		var boardHeight;
		var $main = $('.main');

		this.listenTo(this.model.players, 'sort', this.render);
		this.listenTo(this.model.players, 'sync');

		this.playerEntryHeight = 50;
		this.columnWidth = 400;
		$(window).on('resize', function() {
			boardHeight = $('body').height() - topHeight - 10;
			_this.playersInColumn = Math.floor((boardHeight - _this.playerEntryHeight - 20) / _this.playerEntryHeight);
			$main.css('height', boardHeight);
			_this.render();
		}).resize();
	},

	render: function() {

		for(var i = 0; i < this.model.players.models.length; i++) {

			var player = this.model.players.models[i].attributes;
			player.id = player.id.replace(' ', '_');
			var $playerEntry = this.$el.find('#player_' + player.id);

			if(!$playerEntry.get(0)) {
				$playerEntry = $(this.template({
					player: player
				}));
				this.$el.append($playerEntry);
			}

			$playerEntry.find('.moves').html(player.moves);
			$playerEntry.find('.score').html(player.score);
			$playerEntry.find('.position').html(i + 1);

			var animate = {
				top: i * this.playerEntryHeight + this.playerEntryHeight + 20,
				left: 0
			};

			if(i + 1 > this.playersInColumn) {
				animate.left = '100%';
				animate.top -= (this.playersInColumn) * this.playerEntryHeight;
			}
			$playerEntry.stop(true).animate(animate, 300);
		}

		if(this.model.players.models.length < this.playersInColumn + 1) {
			this.$el.removeClass('two-columns');
		} else {
			this.$el.addClass('two-columns');
		}
	}
});

var PlayerBoard = Backbone.View.extend({
	template: _.template(
		'<table>' +
		'<% for (var x = 0; x < board.length; ++x) { %>' +
			'<tr>' +
			'<% for (var y = 0; y < board[x].length; ++y) { %>' +
				'<td><%- ARROWS[board[x][y].direction] %></td>' +
			'<% } %>' +
			'</tr>' +
		'<% } %>' +
		'</table>'
	),

	initialize: function(options) {
		if (this.collection) {
			this.listenTo(this.collection, 'sync');
		}
	},

	show: function(model) {
		if (this.model) {
			this.stopListening(this.model);
		}

		this.model = model;

		if (this.model) {
			this.listenTo(this.model, 'change', this.render);
			this.listenTo(this.model, 'sync');
		}

		this.render();
	},

	render: function() {
		var ARROWS = {
			'up': '^',
			'down': 'v',
			'left': '<',
			'right': '>',
		};
		var board = this.model.get('board');

		this.$el.empty();
		this.$el.append($('<h3>').html('player:' + this.model.id + ' <small>points:' + this.model.get('score') + ' moves:' + this.model.get('moves') + '</small>'));
		this.$el.append($('<p>').text(this.model.get('moved')));

		if (board) {
			this.$el.append(this.template({
				'board': board,
				'ARROWS': ARROWS,
			}));
		}
	},
});
